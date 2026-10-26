# Original LZW example: https://stackoverflow.com/a/77656917
# Posted by Yousef Javaherian; retrieved 2026-10-20, CC BY-SA 4.0.
# Reworked into standard LZ78 with binary file input/output.


def LZ78_decompress(input: list[tuple[int, bytes]]) -> bytes:
    tree = [b""]
    output = []
    for index, symbol in input:
        entry = tree[index] + symbol
        output.append(entry)
        if symbol:
            tree.append(entry)
    return b"".join(output)


def decompress_file(source="compressed", destination="out.txt"):
    with open(source, "rb") as fin:
        header = fin.read(5)
        payload = fin.read()
    width = header[4]
    pair_size = width + 1
    pairs = [(int.from_bytes(payload[i:i + width], "little"),
              payload[i + width:i + pair_size])
             for i in range(0, len(payload), pair_size)]
    restored = LZ78_decompress(pairs)
    with open(destination, "wb") as fout:
        fout.write(restored)


decompress_file()
    
