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

def build_huffman_tree(chars, freq):
    # Only encoding needs heapq; decoding reads the saved tree directly.
    import heapq

    # Create a min heap of nodes
    priority_queue = [Node(char, f) for char, f in zip(chars, freq)]
    heapq.heapify(priority_queue)

    # Build the Huffman tree
    while len(priority_queue) > 1:
        left_child = heapq.heappop(priority_queue)
        right_child = heapq.heappop(priority_queue)
        merged_node = Node(frequency=left_child.frequency + right_child.frequency)
        merged_node.left = left_child
        merged_node.right = right_child
        heapq.heappush(priority_queue, merged_node)

    return priority_queue[0] if priority_queue else None

def generate_huffman_codes(node, code="", huffman_codes=None):
    if huffman_codes is None:
        huffman_codes = {}

    if node is not None:
        if node.symbol is not None:
            huffman_codes[node.symbol] = code or "0"
        generate_huffman_codes(node.left, code + "0", huffman_codes)
        generate_huffman_codes(node.right, code + "1", huffman_codes)

    return huffman_codes

def serialize_tree(node):
    # Preorder format: 0 = internal node; 1 followed by a byte = leaf.
    if node is None:
        return b""
    if node.symbol is not None:
        return bytes([1, len(node.symbol)]) + node.symbol
    return b"\x00" + serialize_tree(node.left) + serialize_tree(node.right)


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


def compress_file(source="austen.txt", destination="./huffman/compressed_huffman", n_bytes=2):
    with open(source, "rb") as fin:
        data = fin.read()
    frequencies = {}
    for i in range(0, len(data), n_bytes):
        symbol = data[i:i + n_bytes]
        frequencies[symbol] = frequencies.get(symbol, 0) + 1
    root = build_huffman_tree(frequencies.keys(), frequencies.values())
    codes = {symbol: (int(code, 2), len(code))
             for symbol, code in generate_huffman_codes(root).items()}

    # Pack variable-length codes into bytes, most significant bit first.
    payload = bytearray()
    buffer = 0
    bits = 0
    for i in range(0, len(data), n_bytes):
        symbol = data[i:i + n_bytes]
        code, width = codes[symbol]
        buffer = (buffer << width) | code
        bits += width
        while bits >= 8:
            bits -= 8
            payload.append(buffer >> bits)
            buffer &= (1 << bits) - 1
    if bits:
        payload.append(buffer << (8 - bits))

    tree_data = serialize_tree(root)
    # Header: magic (4 bytes), original byte count (8, little-endian),
    # tree byte count (2, little-endian), then the tree and packed payload.
    # The original count tells the decoder when to stop before padding bits.
    with open(destination, "wb") as fout:
        fout.write(b"HUF2")
        fout.write(len(data).to_bytes(8, "little"))
        fout.write(len(tree_data).to_bytes(2, "little"))
        fout.write(tree_data)
        fout.write(payload)


def decompress_file(source="./huffman/compressed_huffman", destination="./huffman/out_huffman.txt"):
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
    compress_file()
    decompress_file()
    with open("austen.txt", "rb") as fin, open("./huffman/out_huffman.txt", "rb") as fout:
        if fin.read() != fout.read():
            raise ValueError("Decompressed output does not match austen.txt")
    print("Created compressed_huffman and out_huffman.txt; exact match verified.")
