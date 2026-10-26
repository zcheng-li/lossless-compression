# Original LZW example: https://stackoverflow.com/a/77656917
# Posted by Yousef Javaherian; retrieved 2026-10-20, CC BY-SA 4.0.
# Reworked into standard LZ78 with binary file input/output.


def LZ78_compress(input: bytes) -> list[tuple[int, bytes]]:
    # Index 0 represents the empty phrase. New phrases start at index 1.
    tree = {b"": 0}
    output = []
    w = b""
    for value in input:
        x = bytes([value])
        phrase = w + x
        if phrase in tree:
            w = phrase
        else:
            output.append((tree[w], x))
            tree[phrase] = len(tree)
            w = b""
    if w:
        # A final known phrase has no following byte; preserve its index.
        output.append((tree[w], b""))
    return output



def compress_file(source="austen.txt", destination="./LZ78/compressed"):
    with open(source, "rb") as fin:
        pairs = LZ78_compress(fin.read())

    # Format: b"LZ78", one byte giving the index width, then pairs of
    # (little-endian index, one literal byte). A final index without a
    # literal represents the remaining known phrase. No dictionary is stored.
    largest_index = max((index for index, _ in pairs), default=0)
    width = max(1, (largest_index.bit_length() + 7) // 8)
    with open(destination, "wb") as fout:
        fout.write(b"LZ78" + bytes([width]))
        fout.write(b"".join(index.to_bytes(width, "little") + symbol
                            for index, symbol in pairs))


if __name__ == "__main__":
    compress_file()
    