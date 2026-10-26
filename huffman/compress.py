# Original Huffman coding example: https://www.geeksforgeeks.org/dsa/huffman-coding-in-python/
# Posted by Geeksforgeeks; retrieved 2026-10-20, CC BY-SA 4.0.
# Reworked into standard Huffman coding with binary file input/output.

import os

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
    if node is None:
        return b""

    def max_symbol_size(current):
        if current.symbol is not None:
            return len(current.symbol)
        return max(max_symbol_size(current.left), max_symbol_size(current.right))

    # One header byte gives the bit width of (symbol length - 1).
    # For one- or two-byte symbols, the length field needs only one bit.
    length_bits = max(1, (max_symbol_size(node) - 1).bit_length())
    tree_data = bytearray([length_bits])
    buffer = 0
    bits = 0

    def write_bits(value, width):
        nonlocal buffer, bits
        buffer = (buffer << width) | value
        bits += width
        while bits >= 8:
            bits -= 8
            tree_data.append(buffer >> bits)
            buffer &= (1 << bits) - 1

    def write_node(current):
        # Preorder: 0 = internal; 1 + length field + symbol bits = leaf.
        if current.symbol is not None:
            write_bits(1, 1)
            write_bits(len(current.symbol) - 1, length_bits)
            for byte in current.symbol:
                write_bits(byte, 8)
        else:
            write_bits(0, 1)
            write_node(current.left)
            write_node(current.right)

    write_node(node)
    if bits:
        tree_data.append(buffer << (8 - bits))
    return bytes(tree_data)


def compress_file(source="austen.txt", destination="./huffman/compressed", n_bytes=2):
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
        fout.write(b"HUF3")
        fout.write(len(data).to_bytes(8, "little"))
        fout.write(len(tree_data).to_bytes(2, "little"))
        fout.write(tree_data)
        fout.write(payload)



if __name__ == "__main__":
    compress_file()
    print("Compression complete. Output written to ./huffman/compressed")
    print("The compressed size is", os.path.getsize("./huffman/compressed") / (1024 * 1024), "MB.")
