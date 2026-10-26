# Source - https://stackoverflow.com/a/77656917
# Posted by Yousef Javaherian
# Retrieved 2026-10-20, License - CC BY-SA 4.0

# Adapted for binary file input/output. The algorithm is LZW, a variant of LZ78.


def LZW_decompress(input):
    if not input:
        return b""
    tree = {i: bytes([i]) for i in range(256)}
    w = tree[input[0]]
    output = [w]
    for code in input[1:]:
        if code in tree:
            entry = tree[code]
        else:
            # For valid LZW input, the missing code is the next dictionary entry.
            entry = w + w[:1]
        output.append(entry)
        tree[len(tree)] = w + entry[:1]
        w = entry
    return b"".join(output)

def decompress_file(source="compressed", destination="out.txt"):
    with open(source, "rb") as fin:
        header = fin.read(1)
        payload = fin.read()
    width = header[0]
    codes = [int.from_bytes(payload[i:i + width], "little")
             for i in range(0, len(payload), width)]
    with open(destination, "wb") as fout:
        fout.write(LZW_decompress(codes))


decompress_file()
   
