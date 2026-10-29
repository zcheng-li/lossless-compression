# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["python-minifier==3.2.0"]
# ///
"""Collect reproducible report measurements without modifying the codecs.

Run from any directory:
    uv run --python 3.12.4 experiments/run_experiments.py
See README.md in this directory for outputs and resume behavior.
"""

from __future__ import annotations

import argparse
import ast
import copy
import csv
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import py_compile
import re
import runpy
import shutil
import signal
import statistics
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[1]
FT = "PPMD+UE+arithmetic+FT"
UE = "PPMD+UE+arithmetic"
NATIVE = {"huffman": "huffman", "arithmetic": "arithmetic", "lz78": "LZ78", "lzw": "LZW"}
GROUPS = ("order", "weights", "design", "algorithms")
MINIFIER_FLAGS = ["--rename-globals", "--remove-literal-statements", "--prefer-single-line"]
SCHEMA = 1


@dataclass(frozen=True)
class Case:
    case_id: str
    label: str
    family: str = "ppm"
    order: int | None = 5
    alpha: int | None = 200
    beta: int | None = 86
    discount: int | None = 0
    update_exclusion: bool | None = True
    header: str = "compact"


def make_plan(orders, betas, selected_groups):
    cases = {}
    groups = {name: [] for name in selected_groups}

    def add(group, case):
        if case.case_id in cases and cases[case.case_id] != case:
            raise ValueError(f"Conflicting case: {case.case_id}")
        cases[case.case_id] = case
        if case.case_id not in groups[group]:
            groups[group].append(case.case_id)

    def tuned(order=5, beta=86):
        return Case(f"ft-k{order}-b{beta}", f"Tuned PPM, K={order}, beta={beta}", order=order, beta=beta)

    if "order" in groups:
        for order in orders:
            add("order", tuned(order=order))
    if "weights" in groups:
        for beta in betas:
            add("weights", tuned(beta=beta))
    if "design" in groups:
        for case in (
            Case("ppmc", "PPM-C", alpha=1, beta=1, update_exclusion=False, header="legacy"),
            Case("ppmd", "Standard PPM-D", alpha=2, beta=1, discount=1, update_exclusion=False, header="legacy"),
            Case("modified", "Modified symbol weight 2c", alpha=2, beta=1, update_exclusion=False, header="legacy"),
            Case("modified-ue", "Modified weights + UE", alpha=2, beta=1, header="legacy"),
            Case("tuned-legacy", "UE + tuned weights (legacy format)", header="legacy"),
            tuned(),
        ):
            add("design", case)
    if "algorithms" in groups:
        for method, label in (
            ("huffman", "Huffman (two-byte groups)"),
            ("arithmetic", "Context-free arithmetic coding"),
            ("lz78", "LZ78"),
            ("lzw", "LZW"),
        ):
            add("algorithms", Case(method, label, method, None, None, None, None, None, "native"))
        add("algorithms", tuned())
    return list(cases.values()), groups


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def object_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def save_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def method(tree, name):
    model = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "PPMModel")
    return next(node for node in model.body if isinstance(node, ast.FunctionDef) and node.name == name)


def same_ast(first, second):
    return ast.dump(first, include_attributes=False) == ast.dump(second, include_attributes=False)


def variant_source(source, case, *, encoder, full_update):
    """Patch model ASTs in copies; fail if a template no longer has the expected rule."""
    tree = ast.parse(source)
    original = copy.deepcopy(tree)
    base_alpha, base_beta = (200, 86) if case.header == "compact" else (2, 1)

    class Weights(ast.NodeTransformer):
        symbols = 0
        escapes = 0

        def visit_Tuple(self, node):
            if not isinstance(node.ctx, ast.Load) or len(node.elts) != 2:
                return self.generic_visit(node)
            event, weight = node.elts
            if isinstance(event, ast.Name) and event.id == "symbol":
                # Do not modify the order -1 weights, or comprehension targets.
                if not any(isinstance(n, ast.Name) and n.id == "count" for n in ast.walk(weight)):
                    return node
                expected = ast.parse(f"{base_alpha} * count", mode="eval").body
                if not same_ast(weight, expected):
                    raise ValueError("Symbol weight template changed; inspect before benchmarking")
                expression = "count" if case.alpha == 1 else f"{case.alpha} * count"
                if case.discount:
                    expression += f" - {case.discount}"
                node.elts[1] = ast.parse(expression, mode="eval").body
                self.symbols += 1
            elif isinstance(event, ast.Name) and event.id == "ESCAPE":
                base = weight
                if base_beta != 1:
                    if not (isinstance(weight, ast.BinOp) and isinstance(weight.op, ast.Mult)
                            and isinstance(weight.left, ast.Constant) and weight.left.value == base_beta):
                        raise ValueError("Escape weight template changed; inspect before benchmarking")
                    base = weight.right
                elif not (isinstance(base, ast.Name) and base.id == "escape_count"
                          or isinstance(base, ast.Call) and isinstance(base.func, ast.Name) and base.func.id == "len"):
                    raise ValueError("Unexpected escape-count expression")
                node.elts[1] = base if case.beta == 1 else ast.BinOp(ast.Constant(case.beta), ast.Mult(), base)
                self.escapes += 1
            return node

    transformer = Weights()
    transformer.visit(method(tree, "distributions"))
    if (transformer.symbols, transformer.escapes) != (1, 1):
        raise ValueError("Expected exactly one symbol-weight and one escape-weight expression")

    order_assignments = 0
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "MAX_ORDER" for t in node.targets):
            node.value = ast.Constant(case.order)
            order_assignments += 1
    if order_assignments != (1 if encoder or case.header == "legacy" else 0):
        raise ValueError("Unexpected MAX_ORDER declarations")

    if not case.update_exclusion:
        model = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "PPMModel")
        index = next(i for i, node in enumerate(model.body) if isinstance(node, ast.FunctionDef) and node.name == "update")
        model.body[index] = copy.deepcopy(full_update)

    if case.header == "compact":
        history_assignment = next(
            node for node in ast.walk(method(tree, "update"))
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Attribute) and t.attr == "history" for t in node.targets
            )
        )
        if case.order == 0:
            history_assignment.value = ast.Constant(b"")
        elif not encoder:
            value = history_assignment.value
            if not (isinstance(value, ast.Subscript) and isinstance(value.slice, ast.Slice)
                    and isinstance(value.slice.lower, ast.UnaryOp)
                    and isinstance(value.slice.lower.op, ast.USub)
                    and isinstance(value.slice.lower.operand, ast.Constant)
                    and value.slice.lower.operand.value == 5):
                raise ValueError("Compact decoder's history limit changed")
            value.slice.lower.operand = ast.Constant(case.order)

    ast.fix_missing_locations(tree)
    # Measure the actual current FT sources for the final configuration.
    if case == Case("ft-k5-b86", "Tuned PPM, K=5, beta=86"):
        if not same_ast(tree, original):
            raise ValueError("Final FT source does not match the experiment's recorded configuration")
        return source
    return ast.unparse(tree) + "\n"


def materialize_sources(case, directory, source_root):
    if case.family != "ppm":
        relative = NATIVE[case.family]
        for filename in ("compress.py", "decompress.py"):
            shutil.copyfile(source_root / relative / filename, directory / filename)
        return
    template = FT if case.header == "compact" else UE
    full_update = method(ast.parse((source_root / "PPM+arithmetic/decompress.py").read_text()), "update")
    for filename in ("compress.py", "decompress.py"):
        source = (source_root / template / filename).read_text(encoding="utf-8")
        generated = variant_source(source, case, encoder=filename == "compress.py", full_update=full_update)
        (directory / filename).write_text(generated, encoding="utf-8")


def encode_worker(case_path, input_path):
    case = Case(**json.loads(case_path.read_text()))
    directory = case_path.parent
    namespace = runpy.run_path(str(directory / "compress.py"), run_name="experiment_encoder")
    if case.family == "ppm":
        payload = namespace["arithmetic_compress"](input_path.read_bytes())
        (directory / "compressed").write_bytes(payload)
    else:
        options = {"n_bytes": 2} if case.family == "huffman" else {}
        namespace["compress_file"](source=str(input_path), destination=str(directory / "compressed"), **options)


def run_process(command, directory, stem, timeout):
    """Keep logs and stop the whole child process group on timeout/interruption."""
    environment = dict(os.environ, LC_ALL="C", PYTHONHASHSEED="0")
    started = time.perf_counter()
    with (directory / f"{stem}.stdout.log").open("wb") as out, (directory / f"{stem}.stderr.log").open("wb") as err:
        process = subprocess.Popen(command, cwd=directory, env=environment, stdout=out, stderr=err, start_new_session=True)
        try:
            code = process.wait(timeout=timeout)
        except BaseException:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            raise
    if code:
        raise RuntimeError(f"{stem} exited with {code}; see {directory / (stem + '.stderr.log')}")
    return time.perf_counter() - started


MINIFY_BOOTSTRAP = (
    "import sys; from importlib.metadata import distribution; sys.argv[0]='pyminify'; "
    "next(e for e in distribution('python-minifier').entry_points if e.name=='pyminify').load()()"
)


def imports_in(source):
    modules = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.add((node.module or "").split(".")[0])
    return sorted(modules)


def verify_output(original, restored):
    if not restored.is_file():
        raise RuntimeError("Decoder did not create out.txt")
    with original.open("rb") as expected, restored.open("rb") as actual:
        while True:
            left, right = expected.read(1024 * 1024), actual.read(1024 * 1024)
            if left != right:
                raise RuntimeError("Decoded output differs from the input")
            if not left:
                return sha256(restored)


def collect_case(case, directory, source_root, input_path, input_sha256, contract_hash, repeats, timeout, force):
    fingerprint = object_hash({"contract": contract_hash, "case": asdict(case)})
    result_path = directory / "result.json"
    if not force and result_path.exists():
        cached = json.loads(result_path.read_text())
        if cached.get("fingerprint") == fingerprint and cached.get("status") == "verified":
            hashes = cached.get("artifact_sha256", {})
            if hashes and all((directory / name).is_file() and sha256(directory / name) == digest for name, digest in hashes.items()):
                print(f"  resume: {case.case_id}", flush=True)
                return cached

    directory.mkdir(parents=True, exist_ok=True)
    result = {**asdict(case), "fingerprint": fingerprint, "status": "running", "repeats": [],
              "artifact_dir": str(directory), "original_bytes": input_path.stat().st_size}
    if case.family == "ppm":
        result["escape_ratio"] = case.beta / case.alpha
    save_json(result_path, result)
    try:
        materialize_sources(case, directory, source_root)
        save_json(directory / "case.json", asdict(case))
        result["encode_wall_seconds"] = run_process(
            [sys.executable, str(Path(__file__).resolve()), "_encode", str(directory / "case.json"), str(input_path)],
            directory, "encode", timeout,
        )
        compressed = directory / "compressed"
        result["compressed_bytes"] = compressed.stat().st_size
        if case.family == "ppm":
            header_size = 4 if case.header == "compact" else 13
            result["header_bytes"] = header_size
            result["payload_bytes"] = compressed.stat().st_size - header_size
            result["payload_sha256"] = hashlib.sha256(compressed.read_bytes()[header_size:]).hexdigest()

        run_process([sys.executable, "-c", MINIFY_BOOTSTRAP, "decompress.py", *MINIFIER_FLAGS,
                     "--output", "decompress.min.py"], directory, "minify", timeout)
        py_compile.compile(str(directory / "decompress.min.py"), cfile=str(directory / "decompress.min.pyc"),
                           dfile="decompress.py", doraise=True, optimize=0)
        result["decoder_pyc_bytes"] = (directory / "decompress.min.pyc").stat().st_size
        modules = imports_in((directory / "decompress.min.py").read_text())
        result["decoder_imports"] = modules
        result["allowed_imports_only"] = set(modules).issubset({"struct", "decimal"})

        for repeat in range(1, repeats + 1):
            restored = directory / "out.txt"
            restored.unlink(missing_ok=True)
            stem = f"decode-{repeat}"
            run_process(["/usr/bin/time", "-p", sys.executable, "decompress.min.pyc"], directory, stem, timeout)
            timing_text = (directory / f"{stem}.stderr.log").read_text()
            timing = {name: float(value) for name, value in re.findall(r"^(real|user|sys)\s+([0-9.]+)\s*$", timing_text, re.M)}
            if set(timing) != {"real", "user", "sys"}:
                raise RuntimeError(f"Cannot parse POSIX timing in {stem}.stderr.log")
            decoded_hash = verify_output(input_path, restored)
            if decoded_hash != input_sha256:
                raise RuntimeError("Input changed after the benchmark metadata was recorded")
            result["repeats"].append({"repeat": repeat, "user_seconds": timing["user"],
                                      "system_seconds": timing["sys"], "wall_seconds": timing["real"],
                                      "decoded_sha256": decoded_hash})
            save_json(result_path, result)

        result["decode_user_seconds"] = statistics.median(r["user_seconds"] for r in result["repeats"])
        result["decode_system_seconds"] = statistics.median(r["system_seconds"] for r in result["repeats"])
        result["decode_wall_seconds"] = statistics.median(r["wall_seconds"] for r in result["repeats"])
        result["decode_user_min_seconds"] = min(r["user_seconds"] for r in result["repeats"])
        result["decode_user_max_seconds"] = max(r["user_seconds"] for r in result["repeats"])
        result["decode_repeats"] = repeats
        result["user_cpu_limit_met"] = all(r["user_seconds"] <= 1200 for r in result["repeats"])
        result["total_bytes"] = result["compressed_bytes"] + result["decoder_pyc_bytes"]
        size = result["original_bytes"]
        result["compressed_ratio_percent"] = 100 * result["compressed_bytes"] / size if size else None
        result["total_ratio_percent"] = 100 * result["total_bytes"] / size if size else None
        result["artifact_sha256"] = {name: sha256(directory / name) for name in (
            "compress.py", "decompress.py", "compressed", "decompress.min.py", "decompress.min.pyc", "out.txt"
        )}
        result["status"] = "verified"
    except KeyboardInterrupt:
        result["status"] = "interrupted"
        save_json(result_path, result)
        raise
    except Exception as error:
        result["status"] = "failed"
        result["error"] = f"{type(error).__name__}: {error}"
    result["finished_utc"] = datetime.now(timezone.utc).isoformat()
    save_json(result_path, result)
    return result


CSV_FIELDS = [
    "case_id", "label", "groups", "status", "family", "order", "alpha", "beta", "escape_ratio", "discount",
    "update_exclusion", "header", "original_bytes", "compressed_bytes", "header_bytes", "payload_bytes",
    "decoder_pyc_bytes", "total_bytes", "compressed_ratio_percent", "total_ratio_percent",
    "encode_wall_seconds", "decode_user_seconds", "decode_user_min_seconds", "decode_user_max_seconds",
    "decode_system_seconds", "decode_wall_seconds", "decode_repeats", "allowed_imports_only",
    "decoder_imports", "user_cpu_limit_met", "artifact_dir", "error",
]


def write_summary(output, metadata, groups, results):
    # Header compaction must leave the arithmetic payload unchanged.
    checks = {}
    old, final = results.get("tuned-legacy"), results.get("ft-k5-b86")
    if old and final and old.get("status") == final.get("status") == "verified":
        checks["compact_header_preserves_payload"] = old["payload_sha256"] == final["payload_sha256"]
        checks["header_savings_bytes"] = old["compressed_bytes"] - final["compressed_bytes"]
        if not checks["compact_header_preserves_payload"] or checks["header_savings_bytes"] != 9:
            raise RuntimeError("Legacy/compact payload comparison failed; inspect saved sources before reporting gains")
    summary = {"schema": SCHEMA, "metadata": metadata, "groups": groups, "checks": checks, "results": list(results.values())}
    save_json(output / "results.json", summary)

    def write_csv(path, case_ids):
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, extrasaction="ignore")
            writer.writeheader()
            for case_id in case_ids:
                if case_id not in results:
                    continue
                row = dict(results[case_id])
                row["groups"] = ";".join(g for g, ids in groups.items() if case_id in ids)
                row["decoder_imports"] = ";".join(row.get("decoder_imports", []))
                writer.writerow(row)
    write_csv(output / "results.csv", list(results))
    for group, case_ids in groups.items():
        write_csv(output / f"{group}.csv", case_ids)


def cpu_name():
    if sys.platform == "darwin":
        probe = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True)
        if probe.returncode == 0:
            return probe.stdout.strip()
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        match = re.search(r"^model name\s*:\s*(.+)$", cpuinfo.read_text(), re.M)
        if match:
            return match.group(1)
    return platform.processor() or platform.machine()


def setup_metadata(output, input_path, repeats, timeout):
    source_paths = [Path(__file__).resolve()]
    for folder in (FT, UE, "PPM+arithmetic", *NATIVE.values()):
        source_paths.extend(ROOT / folder / name for name in ("compress.py", "decompress.py"))
    source_hashes = {str(path.relative_to(ROOT)): sha256(path) for path in source_paths}
    contract = {
        "schema": SCHEMA, "input_sha256": sha256(input_path), "input_bytes": input_path.stat().st_size,
        "python_version": sys.version, "python_executable": sys.executable,
        "os": platform.platform(), "cpu": cpu_name(), "machine": platform.machine(),
        "logical_cpus": os.cpu_count(), "python_minifier_version": importlib.metadata.version("python-minifier"),
        "minifier_flags": MINIFIER_FLAGS, "compile_optimize": 0, "compile_filename": "decompress.py",
        "decode_repeats": repeats, "process_timeout_seconds": timeout, "sources": source_hashes,
    }
    contract_hash = object_hash(contract)
    metadata_path = output / "metadata.json"
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text())
        if metadata["contract_hash"] != contract_hash:
            raise ValueError("Input, sources, runtime, host, or measurement settings changed. Choose a new --output directory.")
    else:
        metadata = {"created_utc": datetime.now(timezone.utc).isoformat(), "input_path": str(input_path),
                    "contract_hash": contract_hash, **contract}
        save_json(metadata_path, metadata)
    snapshot = output / "sources"
    for path in source_paths:
        destination = snapshot / path.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if sha256(destination) != source_hashes[str(path.relative_to(ROOT))]:
                raise ValueError(f"Saved source snapshot was modified: {destination}")
        else:
            shutil.copyfile(path, destination)
    return metadata, snapshot


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=ROOT / "austen.txt")
    parser.add_argument("--output", type=Path, default=ROOT / "experiments/results")
    parser.add_argument("--groups", nargs="+", choices=GROUPS, default=list(GROUPS))
    parser.add_argument("--orders", nargs="+", type=int, default=[4, 5, 6])
    parser.add_argument("--betas", nargs="+", type=int, default=[110, 100, 95, 90, 88, 87, 86, 85, 80])
    parser.add_argument("--repeats", type=int, default=3, help="Independent decoder runs; save all times and report their median")
    parser.add_argument("--timeout", type=float, default=1800, help="Wall-time limit in seconds for each child process")
    parser.add_argument("--force", action="store_true", help="Recompute already verified cases in the same output directory")
    parser.add_argument("--list", action="store_true", help="Print the plan without installing dependencies or running measurements")
    args = parser.parse_args(argv)
    if not args.orders or any(not 0 <= k <= 255 for k in args.orders):
        parser.error("Orders must be in 0..255")
    if any(beta <= 0 for beta in args.betas) or args.repeats < 1 or args.timeout <= 0:
        parser.error("Betas, repeats, and timeout must be positive")
    cases, groups = make_plan(args.orders, args.betas, args.groups)
    if args.list:
        for case in cases:
            member = ", ".join(g for g, ids in groups.items() if case.case_id in ids)
            print(f"{case.case_id:18} {case.label:42} [{member}]")
        print(f"{len(cases)} unique cases; {args.repeats} decoder runs per case.")
        return 0
    if sys.version_info[:2] != (3, 12):
        parser.error("Use Python 3.12 for comparable bytecode sizes; the README recommends 3.12.4")
    if os.name != "posix" or not Path("/usr/bin/time").is_file():
        parser.error("This collector requires macOS/Linux and /usr/bin/time")
    try:
        importlib.metadata.version("python-minifier")
    except importlib.metadata.PackageNotFoundError:
        parser.error("python-minifier is missing. Run this script with uv as shown in README.md")
    input_path = args.input.resolve()
    if not input_path.is_file():
        parser.error(f"Input does not exist: {input_path}")
    output = args.output.resolve()
    # Avoid ever placing generated files inside a source codec directory.
    if output == ROOT or any(output == ROOT / folder or ROOT / folder in output.parents for folder in (FT, UE, "PPM+arithmetic", *NATIVE.values(), "submission")):
        parser.error("Choose an output directory outside the source codec/submission directories")
    output.mkdir(parents=True, exist_ok=True)
    try:
        metadata, source_root = setup_metadata(output, input_path, args.repeats, args.timeout)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    results = {}
    summary_path = output / "results.json"
    if summary_path.exists():
        old = json.loads(summary_path.read_text())
        results = {row["case_id"]: row for row in old["results"]}
        groups = {**old["groups"], **groups}
    print(f"Input: {input_path} ({metadata['input_bytes']:,} bytes)", flush=True)
    print(f"Python: {platform.python_version()}; results: {output}", flush=True)
    print(f"{len(cases)} unique cases; sequential execution; {args.repeats} decoder runs per case.", flush=True)
    try:
        for index, case in enumerate(cases, 1):
            print(f"[{index}/{len(cases)}] {case.case_id}: {case.label}", flush=True)
            directory = output / "cases" / case.case_id
            try:
                row = collect_case(case, directory, source_root, input_path, metadata["input_sha256"], metadata["contract_hash"],
                                   args.repeats, args.timeout, args.force)
            except KeyboardInterrupt:
                if (directory / "result.json").exists():
                    results[case.case_id] = json.loads((directory / "result.json").read_text())
                raise
            results[case.case_id] = row
            write_summary(output, metadata, groups, results)
            if row["status"] == "verified":
                ratio = row["total_ratio_percent"]
                ratio_text = f"{ratio:.4f}%" if ratio is not None else "undefined (empty input)"
                print(f"  verified: C={row['compressed_bytes']:,}, D={row['decoder_pyc_bytes']:,}, "
                      f"total={ratio_text}, median decode user={row['decode_user_seconds']:.2f}s", flush=True)
            else:
                print(f"  FAILED: {row.get('error', row['status'])}", flush=True)
    except KeyboardInterrupt:
        write_summary(output, metadata, groups, results)
        print("\nInterrupted. Completed results are saved; repeat the same command to resume.", flush=True)
        return 130
    failed = [case.case_id for case in cases if results[case.case_id]["status"] != "verified"]
    print(f"Saved JSON, combined CSV, and group CSVs in {output}", flush=True)
    if failed:
        print("Failed cases (rerun to retry): " + ", ".join(failed), flush=True)
    return int(bool(failed))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "_encode":
        encode_worker(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        raise SystemExit(main())
