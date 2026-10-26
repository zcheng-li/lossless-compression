#!/usr/bin/env bash
set -euo pipefail

# Usage: bash check.sh DECODER COMPRESSED [PYTHON] [ORIGINAL]
# The decoder must read ./compressed and write ./out.txt without other files.
if [[ $# -lt 2 || $# -gt 4 ]]; then
    echo "用法：bash check.sh 解压脚本 压缩文件 [Python命令] [原始文件]" >&2
    echo "示例：bash check.sh huffman/decompress.py huffman/compressed_huffman python3.12" >&2
    exit 1
fi

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
decoder=$1
compressed=$2
python_cmd=${3:-python3}
original=${4:-"$script_dir/austen.txt"}

for file in "$decoder" "$compressed" "$original"; do
    if [[ ! -f "$file" ]]; then
        echo "找不到文件：$file" >&2
        exit 1
    fi
done

# Resolve Python before changing to the isolated working directory.
python_cmd=$("$python_cmd" -c 'import sys; print(sys.executable)')
"$python_cmd" --version
echo "解压脚本：$decoder"
echo "压缩文件：$compressed"

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
    echo "解压程序运行失败" >&2
    exit 1
fi
awk '$1 == "user" {print "解压用户态 CPU 时间：" $2 " 秒"}' "$work_dir/time.txt"

if cmp -s -- "$original" "$work_dir/out.txt"; then
    echo "验证通过：解压结果与原文件完全一致"
else
    echo "验证失败：out.txt 缺失或内容不一致" >&2
    exit 1
fi

original_size=$(wc -c < "$original")
compressed_size=$(wc -c < "$work_dir/compressed")
decoder_size=$(wc -c < "$pyc_file")

echo "原文件：$original_size 字节"
echo "压缩文件：$compressed_size 字节"
echo "解压器 .pyc：$decoder_size 字节"

awk -v original="$original_size" \
    -v compressed="$compressed_size" \
    -v decoder="$decoder_size" \
    'BEGIN {
        if (original == 0) {
            print "原文件为空，无法计算压缩率"
            exit 1
        }
        printf "压缩率：(%.0f + %.0f) / %.0f = %.4f%%\n",
            compressed, decoder, original,
            100 * (compressed + decoder) / original
    }'
