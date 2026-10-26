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


def LZ78_decompress(input: list[tuple[int, bytes]]) -> bytes:
    tree = [b""]
    output = []
    for position, (index, symbol) in enumerate(input):
        if not 0 <= index < len(tree) or len(symbol) > 1:
            raise ValueError("Invalid LZ78 pair")
        if not symbol and (position != len(input) - 1 or index == 0):
            raise ValueError("An index-only phrase is allowed only at the end")
        entry = tree[index] + symbol
        output.append(entry)
        if symbol:
            tree.append(entry)
    return b"".join(output)


def compress_file(source="austen.txt", destination="compressed_LZ78"):
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


def decompress_file(source="compressed_LZ78", destination="out_LZ78.txt"):
    with open(source, "rb") as fin:
        header = fin.read(5)
        payload = fin.read()
    if len(header) != 5 or header[:4] != b"LZ78" or header[4] == 0:
        raise ValueError("Missing or invalid LZ78 header")
    width = header[4]
    pair_size = width + 1
    if len(payload) % pair_size not in (0, width):
        raise ValueError("Truncated LZ78 index")
    pairs = [(int.from_bytes(payload[i:i + width], "little"),
              payload[i + width:i + pair_size])
             for i in range(0, len(payload), pair_size)]
    restored = LZ78_decompress(pairs)
    with open(destination, "wb") as fout:
        fout.write(restored)


if __name__ == "__main__":
    compress_file()
    decompress_file()
    with open("austen.txt", "rb") as fin, open("out_LZ78.txt", "rb") as fout:
        if fin.read() != fout.read():
            raise ValueError("Decompressed output does not match austen.txt")
    print("Created compressed_LZ78 and out_LZ78.txt; exact match verified.")
