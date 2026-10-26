# Original Huffman coding example: https://www.geeksforgeeks.org/dsa/huffman-coding-in-python/
# Posted by Geeksforgeeks; retrieved 2026-10-20, CC BY-SA 4.0.
# Reworked into standard Huffman coding with binary file input/output.

class Node:
    def __init__(self, symbol=None, frequency=None):
        self.symbol = symbol
        self.frequency = frequency
        self.left = None
        self.right = None

    def __lt__(self, other):
        return self.frequency < other.frequency


def deserialize_tree(data):
    if not data:
        return None

    def read_node(position):
        if position >= len(data):
            raise ValueError("Truncated Huffman tree")
        marker = data[position]
        position += 1
        if marker == 1:
            if position >= len(data):
                raise ValueError("Missing symbol length")
            size = data[position]
            position += 1
            if size not in (1, 2) or position + size > len(data):
                raise ValueError("Invalid leaf symbol")
            symbol = data[position:position + size]
            return Node(symbol=symbol), position + size
        if marker != 0:
            raise ValueError("Invalid Huffman tree marker")
        node = Node()
        node.left, position = read_node(position)
        node.right, position = read_node(position)
        return node, position

    root, position = read_node(0)
    if position != len(data):
        raise ValueError("Unexpected data after Huffman tree")
    return root


def decompress_file(source="compressed", destination="out.txt"):
    with open(source, "rb") as fin:
        header = fin.read(14)
        if len(header) != 14 or header[:4] != b"HUF2":
            raise ValueError("Missing or invalid Huffman header")
        original_size = int.from_bytes(header[4:12], "little")
        tree_size = int.from_bytes(header[12:14], "little")
        tree_data = fin.read(tree_size)
        if len(tree_data) != tree_size:
            raise ValueError("Truncated Huffman tree")
        payload = fin.read()
    root = deserialize_tree(tree_data)
    output = bytearray()
    if root is None:
        if original_size != 0 or payload:
            raise ValueError("Missing Huffman tree")
    elif root.symbol is not None:
        symbol_count, remainder = divmod(original_size, len(root.symbol))
        if remainder or len(payload) != (symbol_count + 7) // 8 or any(payload):
            raise ValueError("Invalid single-symbol Huffman payload")
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
    if len(output) != original_size:
        raise ValueError("Truncated Huffman payload")
    with open(destination, "wb") as fout:
        fout.write(output)


if __name__ == "__main__":
    decompress_file()
