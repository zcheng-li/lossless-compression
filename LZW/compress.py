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


def compress_file(source="austen.txt", destination="./LZW/compressed"):
    with open(source, "rb") as fin:
        codes = LZW_compress(fin.read())

    # File format: one byte giving the code width in bytes, followed by
    # fixed-width unsigned little-endian codes. No dictionary is stored.
    width = max(1, (max(codes, default=0).bit_length() + 7) // 8)
    with open(destination, "wb") as fout:
        fout.write(bytes([width]))
        fout.write(b"".join(code.to_bytes(width, "little") for code in codes))



if __name__ == "__main__":
    compress_file()