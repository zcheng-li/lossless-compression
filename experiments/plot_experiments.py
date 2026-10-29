# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["matplotlib==3.10.7"]
# ///
"""Plot verified experiment results as PDF and PNG without editing the report."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import textwrap


HERE = Path(__file__).resolve().parent
BLUE, ORANGE, GREEN = "#355C7D", "#D98C3F", "#3F7F5F"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=HERE / "results/results.json")
    parser.add_argument("--output", type=Path, help="Default: figures/ beside results.json")
    args = parser.parse_args(argv)
    if not args.results.is_file():
        parser.error(f"Missing results: {args.results}. Run run_experiments.py first.")
    raw_results = args.results.read_bytes()
    summary = json.loads(raw_results)
    if summary.get("schema") != 1:
        parser.error("Unsupported results schema")
    output = args.output.resolve() if args.output else args.results.resolve().parent / "figures"
    output.mkdir(parents=True, exist_ok=True)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator, StrMethodFormatter

    plt.rcParams.update({
        "font.family": "serif", "font.serif": ["DejaVu Serif"], "mathtext.fontset": "cm",
        "font.size": 10, "axes.titlesize": 11, "axes.labelsize": 10,
        "legend.fontsize": 8, "xtick.labelsize": 9, "ytick.labelsize": 9,
        "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42,
        "savefig.dpi": 300,
    })
    rows = {r["case_id"]: r for r in summary["results"]}
    groups = summary["groups"]
    metadata = summary["metadata"]
    if metadata["input_bytes"] == 0:
        parser.error("Compression ratios are undefined for empty input")
    generated = []

    def verified(group, field):
        expected = groups.get(group, [])
        valid = [rows[k] for k in expected if k in rows and rows[k].get("status") == "verified"
                 and isinstance(rows[k].get(field), (int, float)) and math.isfinite(rows[k][field])]
        if len(valid) != len(expected):
            print(f"{group}: using {len(valid)}/{len(expected)} planned cases; incomplete/failed results are excluded.")
        return valid, len(expected)

    def save(fig, stem, included):
        for extension in ("pdf", "png"):
            fig.savefig(output / f"{stem}.{extension}", bbox_inches="tight")
        plt.close(fig)
        generated.append({"stem": stem, "case_ids": [r["case_id"] for r in included]})

    def title(name, count, expected):
        return name if count == expected else f"{name} ({count}/{expected} verified)"

    def curve(group, x_key, stem, heading, xlabel, selected, transform=lambda value: value):
        data, expected = verified(group, "compressed_bytes")
        data.sort(key=lambda r: transform(r[x_key]))
        if not data:
            return
        fig, ax = plt.subplots(figsize=(6.2, 3.8), layout="constrained")
        xs = [transform(r[x_key]) for r in data]
        ys = [r["compressed_bytes"] for r in data]
        ax.plot(xs, ys, color=BLUE, marker="o", linewidth=1.4, label="Verified measurements")
        minimum = min(r["compressed_bytes"] for r in data)
        best = [r for r in data if r["compressed_bytes"] == minimum]
        ax.scatter([transform(r[x_key]) for r in best], [r["compressed_bytes"] for r in best], marker="s", s=70,
                   facecolors="none", edgecolors=GREEN, linewidths=1.6, zorder=4, label="Best measured")
        chosen = [r for r in data if r[x_key] == selected]
        if chosen:
            setting = f"$K={selected}$" if group == "order" else rf"$\rho={transform(selected):.3f}$"
            ax.scatter([transform(selected)], [chosen[0]["compressed_bytes"]], marker="*", s=150,
                       color=ORANGE, zorder=5, label=f"Submission ({setting})")
        ax.set(xlabel=xlabel, ylabel="Compressed size (bytes)", title=title(heading, len(data), expected))
        ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
        ax.yaxis.set_major_locator(MaxNLocator(nbins=6, integer=True))
        if group == "order":
            ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        else:
            ax.xaxis.set_major_locator(MaxNLocator(nbins=6))
            ax.xaxis.set_major_formatter(StrMethodFormatter("{x:.3f}"))
        ax.grid(axis="y", alpha=0.22)
        padding = max(1, (max(ys) - min(ys)) * 0.22)
        ax.set_ylim(max(0, min(ys) - padding), max(ys) + padding)
        ax.margins(x=0.08)
        ax.legend(loc="best", frameon=False)
        save(fig, stem, data)

    curve("order", "order", "context_order", "Context-order selection", "Maximum context order $K$", 5)
    curve("weights", "beta", "escape_weight", "Relative-weight selection", r"Escape ratio $\rho=\beta/200$", 86,
          transform=lambda value: value / 200)

    data, expected = verified("design", "total_ratio_percent")
    if data:
        labels = {
            "ppmc": "PPM-C", "ppmd": "Standard PPM-D", "modified": "Modified weights (2c)",
            "modified-ue": "Modified weights + UE", "tuned-legacy": "UE + tuned weights",
            "ft-k5-b86": "Tuned model + compact format",
        }
        fig, ax = plt.subplots(figsize=(8.4, 4.5), layout="constrained")
        positions = list(range(len(data)))
        compressed = [r["compressed_bytes"] for r in data]
        decoder = [r["decoder_pyc_bytes"] for r in data]
        ax.barh(positions, compressed, color=BLUE, label="Compressed file")
        ax.barh(positions, decoder, left=compressed, color=ORANGE, label="Decoder .pyc")
        maximum = max(r["total_bytes"] for r in data)
        for y, row in enumerate(data):
            ax.text(row["total_bytes"] + maximum * 0.012, y, f"{row['total_ratio_percent']:.4f}%", va="center", fontsize=8)
        ax.set_yticks(positions, [labels.get(r["case_id"], r["label"]) for r in data])
        ax.invert_yaxis()
        ax.set(xlabel="Total stored size (bytes)", title=title("Contribution of design choices", len(data), expected))
        ax.xaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
        ax.set_xlim(0, max(maximum, 1) * 1.21)
        ax.grid(axis="x", alpha=0.2)
        ax.set_axisbelow(True)
        ax.legend(loc="lower right", frameon=False)
        save(fig, "design_comparison", data)

    data, expected = verified("algorithms", "total_ratio_percent")
    if data:
        fig, (size_ax, time_ax) = plt.subplots(1, 2, figsize=(10.5, 4.6), layout="constrained", sharey=True)
        positions = list(range(len(data)))
        labels = []
        for row in data:
            label = "Final tuned PPM + UE" if row["case_id"] == "ft-k5-b86" else row["label"]
            if not row.get("allowed_imports_only", True):
                label += "*"
            labels.append(textwrap.fill(label, width=24))
        colors = [GREEN if r["case_id"] == "ft-k5-b86" else BLUE for r in data]
        ratios = [r["total_ratio_percent"] for r in data]
        size_ax.barh(positions, ratios, color=colors)
        size_ax.set_yticks(positions, labels)
        size_ax.invert_yaxis()
        size_ax.set(xlabel="Total size / original size (%)", title="Storage (compressed + decoder)")
        size_ax.set_xlim(0, max(ratios) * 1.24 if max(ratios) else 1)
        for y, value in enumerate(ratios):
            size_ax.text(value + max(ratios) * 0.015, y, f"{value:.3f}%", va="center", fontsize=8)
        times = [r["decode_user_seconds"] for r in data]
        errors = [[max(0, row["decode_user_seconds"] - row["decode_user_min_seconds"]) for row in data],
                  [max(0, row["decode_user_max_seconds"] - row["decode_user_seconds"]) for row in data]]
        time_ax.barh(positions, times, color=colors, xerr=errors, capsize=3, error_kw={"elinewidth": 0.8})
        maximum = max(r["decode_user_max_seconds"] for r in data)
        time_ax.set_xlim(0, max(maximum, 0.01) * 1.3)
        time_ax.set(xlabel="Decode user CPU time (s)", title="Median; whiskers show min--max")
        for y, row in enumerate(data):
            time_ax.text(row["decode_user_max_seconds"] + max(maximum, 0.01) * 0.015, y,
                         f"{row['decode_user_seconds']:.2f}", va="center", fontsize=8)
        for ax in (size_ax, time_ax):
            ax.grid(axis="x", alpha=0.2)
            ax.set_axisbelow(True)
        fig.suptitle(title("Compression-method comparison", len(data), expected), fontsize=12)
        if any(not r.get("allowed_imports_only", True) for r in data):
            size_ax.set_xlabel("Total size / original size (%)\n* Extra decoder import; see results metadata", fontsize=9)
        save(fig, "algorithm_comparison", data)

    manifest = {
        "results_file": str(args.results.resolve()),
        "results_sha256": hashlib.sha256(raw_results).hexdigest(),
        "input_path": metadata["input_path"], "input_sha256": metadata["input_sha256"],
        "input_bytes": metadata["input_bytes"], "benchmark_contract_hash": metadata["contract_hash"],
        "matplotlib_version": matplotlib.__version__, "figures": generated,
    }
    (output / "plot_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if not generated:
        parser.error("No verified, nonempty-input measurements to plot")
    print(f"Saved {len(generated)} figures as PDF and PNG in {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
