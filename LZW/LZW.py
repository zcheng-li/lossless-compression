# Source - https://stackoverflow.com/a/77656917
# Posted by Yousef Javaherian
# Retrieved 2026-10-20, License - CC BY-SA 4.0

# Adapted for binary file input/output. The algorithm is LZW, a variant of LZ78.


def LZW_compress(input: bytes) -> list[int]:
    if not input:
        return []
    # Both sides start with the same dictionary of all 256 byte values.
    tree = {bytes([i]): i for i in range(256)}
    output = []
    w = b""
    for value in input:
        x = bytes([value])
        if w+x in tree:
            w += x
        else:
            output.append(tree[w])
            tree[w+x] = len(tree)
            w = x
    output.append(tree[w])
    return output


def LZW_decompress(input: list[int]) -> bytes:
    if not input:
        return b""
    tree = {i: bytes([i]) for i in range(256)}
    w = tree[input[0]]
    output = [w]
    for code in input[1:]:
        if code in tree:
            entry = tree[code]
        elif code == len(tree):
            # The next phrase can refer to the entry being created now.
            entry = w + w[:1]
        else:
            raise ValueError("Invalid LZW code")
        output.append(entry)
        tree[len(tree)] = w + entry[:1]
        w = entry
    return b"".join(output)


def compress_file(source="austen.txt", destination="compressed_LZ78"):
    with open(source, "rb") as fin:
        codes = LZW_compress(fin.read())

    # File format: one byte giving the code width in bytes, followed by
    # fixed-width unsigned little-endian codes. No dictionary is stored.
    width = max(1, (max(codes, default=0).bit_length() + 7) // 8)
    with open(destination, "wb") as fout:
        fout.write(bytes([width]))
        fout.write(b"".join(code.to_bytes(width, "little") for code in codes))


def decompress_file(source="compressed_LZ78", destination="out_LZ78.txt"):
    with open(source, "rb") as fin:
        header = fin.read(1)
        payload = fin.read()
    if not header or header[0] == 0:
        raise ValueError("Missing or invalid code width")
    width = header[0]
    if len(payload) % width:
        raise ValueError("Truncated LZW code")
    codes = [int.from_bytes(payload[i:i + width], "little")
             for i in range(0, len(payload), width)]
    with open(destination, "wb") as fout:
        fout.write(LZW_decompress(codes))


if __name__ == "__main__":
    compress_file()
    decompress_file()
    with open("austen.txt", "rb") as fin, open("out_LZ78.txt", "rb") as fout:
        if fin.read() != fout.read():
            raise ValueError("Decompressed output does not match austen.txt")
    print("Created compressed_LZ78 and out_LZ78.txt; exact match verified.")
