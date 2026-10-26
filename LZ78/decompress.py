# Original LZW example: https://stackoverflow.com/a/77656917
# Posted by Yousef Javaherian; retrieved 2026-10-20, CC BY-SA 4.0.
# Reworked into standard LZ78 with binary file input/output.


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


def decompress_file(source="./LZ78/compressed", destination="./LZ78/out.txt"):
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
    decompress_file()
    