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

    def read_node(position):
        marker = data[position]
        position += 1
        if marker == 1:
            size = data[position]
            position += 1
            symbol = data[position:position + size]
            return Node(symbol=symbol), position + size
        node = Node()
        node.left, position = read_node(position)
        node.right, position = read_node(position)
        return node, position

    root, _ = read_node(0)
    return root


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
