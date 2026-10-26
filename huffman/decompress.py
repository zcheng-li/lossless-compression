# Original Huffman coding example: https://www.geeksforgeeks.org/dsa/huffman-coding-in-python/
# Posted by Geeksforgeeks; retrieved 2026-10-20, CC BY-SA 4.0.
# Reworked into standard Huffman coding with binary file input/output.

class Node:
    def __init__(self, symbol=None):
        self.symbol = symbol
        self.left = None
        self.right = None


def deserialize_tree(data):
    if not data:
        return None

    length_bits = data[0]
    position = 8

    def read_bits(width):
        nonlocal position
        value = 0
        for _ in range(width):
            byte = data[position // 8]
            value = (value << 1) | ((byte >> (7 - position % 8)) & 1)
            position += 1
        return value

    def read_node():
        if read_bits(1):
            size = read_bits(length_bits) + 1
            symbol = bytes(read_bits(8) for _ in range(size))
            return Node(symbol=symbol)
        node = Node()
        node.left = read_node()
        node.right = read_node()
        return node

    return read_node()


def decompress_file(source="compressed", destination="out.txt"):
    with open(source, "rb") as fin:
        header = fin.read(14)
        original_size = int.from_bytes(header[4:12], "little")
        tree_size = int.from_bytes(header[12:14], "little")
        tree_data = fin.read(tree_size)
        payload = fin.read()
    root = deserialize_tree(tree_data)
    output = bytearray()
    if root is None:
        pass
    elif root.symbol is not None:
        symbol_count = original_size // len(root.symbol)
        output = root.symbol * symbol_count
    else:
        node = root
        for byte in payload:
            for shift in range(7, -1, -1):
                node = node.right if (byte >> shift) & 1 else node.left
                if node.symbol is not None:
                    output.extend(node.symbol)
                    node = root
                    if len(output) == original_size:
                        break
            if len(output) == original_size:
                break
    with open(destination, "wb") as fout:
        fout.write(output)


decompress_file()
