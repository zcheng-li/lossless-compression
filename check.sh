#!/usr/bin/env bash
set -euo pipefail

# Configuration: relative method paths are resolved next to this script.
method_dir="arithmetic"
python_cmd="python3.12"

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
original="$script_dir/austen.txt"
case "$method_dir" in
    /*) ;;
    *) method_dir="$script_dir/$method_dir" ;;
esac

if [[ ! -d "$method_dir" ]]; then
    echo "Method directory not found: $method_dir" >&2
    exit 1
fi

# Each method directory uses the same filenames.
# The standalone decoder must read ./compressed and write ./out.txt.
decoder="$method_dir/decompress.py"
compressed="$method_dir/compressed"

for file in "$decoder" "$compressed" "$original"; do
    if [[ ! -f "$file" ]]; then
        echo "File not found: $file" >&2
        exit 1
    fi
done

# Resolve Python before changing to the isolated working directory.
python_cmd=$("$python_cmd" -c 'import sys; print(sys.executable)')
"$python_cmd" --version
echo "Decoder: $decoder"
echo "Compressed file: $compressed"

work_dir=$(mktemp -d "${TMPDIR:-/tmp}/lossless-check.XXXXXXXX")
trap 'rm -rf -- "$work_dir"' EXIT
cp -- "$decoder" "$work_dir/decompress.py"
cp -- "$compressed" "$work_dir/compressed"

# Compile the exact standalone decoder being checked, not the encoder.
pyc_file=$("$python_cmd" -c \
    'import py_compile, sys; print(py_compile.compile(sys.argv[1], dfile="decompress.py", doraise=True, optimize=0))' \
    "$work_dir/decompress.py")

# POSIX time -p works on both macOS and Linux. Only decoding is timed.
if ! (cd -- "$work_dir" && LC_ALL=C /usr/bin/time -p "$python_cmd" decompress.py) \
        2>"$work_dir/time.txt"; then
    cat "$work_dir/time.txt" >&2
    echo "Decompression failed" >&2
    exit 1
fi
awk '$1 == "user" {print "Decompression user CPU time: " $2 " seconds"}' "$work_dir/time.txt"

if cmp -s -- "$original" "$work_dir/out.txt"; then
    echo "Verification passed: decompressed output matches the original exactly"
else
    echo "Verification failed: out.txt is missing or differs from the original" >&2
    exit 1
fi

original_size=$(wc -c < "$original")
compressed_size=$(wc -c < "$work_dir/compressed")
decoder_size=$(wc -c < "$pyc_file")

echo "Original size: $original_size bytes"
echo "Compressed size: $compressed_size bytes"
echo "Decoder .pyc size: $decoder_size bytes"

awk -v original="$original_size" \
    -v compressed="$compressed_size" \
    -v decoder="$decoder_size" \
    'BEGIN {
        if (original == 0) {
            print "Cannot calculate the compression ratio: the original file is empty"
            exit 1
        }
        printf "Compression ratio: (%.0f + %.0f) / %.0f = %.4f%%\n",
            compressed, decoder, original,
            100 * (compressed + decoder) / original
    }'
