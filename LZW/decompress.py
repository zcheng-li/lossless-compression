# Source - https://stackoverflow.com/a/77656917
# Posted by Yousef Javaherian
# Retrieved 2026-10-20, License - CC BY-SA 4.0

# Adapted for binary file input/output. The algorithm is LZW, a variant of LZ78.


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

def decompress_file(source="compressed", destination="out.txt"):
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
    decompress_file()
   
