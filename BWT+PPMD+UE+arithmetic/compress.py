"""BWT, PPM with method-D-style weights, full update exclusion and arithmetic coding.

Model reference: W. J. Teahan, Probability estimation for PPM,
https://cotty.16x16.com/compress/peppm.htm (update exclusions).
"""

import os
import struct


STATE_BITS = 64
FULL_RANGE = 1 << STATE_BITS
HALF = FULL_RANGE >> 1
QUARTER = HALF >> 1
MASK = FULL_RANGE - 1
MAX_ORDER = 5
ESCAPE = 256

def bwt_transform(data):
    # Sort cyclic rotations by doubling the compared prefix length each pass.
    # Store rotation 0's row instead of reserving a special end-marker byte.
    size = len(data)
    if size == 0:
        return b"", 0

    rotations = list(range(size))
    ranks = list(data)
    rank_base = max(size, 256)
    width = 1
    while width < size:
        rotations.sort(key=lambda start: ranks[start] * rank_base
                       + ranks[(start + width) % size])
        next_ranks = [0] * size
        rank = 0
        previous = rotations[0]
        for start in rotations[1:]:
            if (ranks[start] != ranks[previous]
                    or ranks[(start + width) % size]
                    != ranks[(previous + width) % size]):
                rank += 1
            next_ranks[start] = rank
            previous = start
        ranks = next_ranks
        if rank == size - 1:
            break
        width *= 2

    last_column = bytes(data[start - 1] for start in rotations)
    return last_column, rotations.index(0)


class PPMModel:
    def __init__(self, max_order=MAX_ORDER):
        self.max_order = max_order

        # Recently processed bytes used as n_order_context to predict the next byte.
        self.history = b""

        # Each n_order_context maps to a frequency table. For example:
        # self.contexts[b"ab"] = {ord("c"): 3, ord("d"): 1}
        # After n_order_context ab, c has appeared 3 times and d has appeared once.
        self.contexts = {}

    def distributions(self):
        # Bytes ruled out by longer contexts are excluded from shorter ones.
        excluded_symbols = set()
        longest_order = len(self.history)

        # For history = b"abc", try abc, bc, c, then the empty n_order_context.
        for order in range(longest_order, -1, -1):
            if order == 0:
                n_order_context = b""
            else:
                n_order_context = self.history[-order:]

            # If this n_order_context has no statistics, try a shorter n_order_context.
            if n_order_context not in self.contexts:
                continue

            counts_table = self.contexts[n_order_context]
            frequencies = []

            # Sort byte values so the encoder and decoder use the same order.
            sorted_symbols = sorted(counts_table.keys())
            for symbol in sorted_symbols:
                if symbol in excluded_symbols:
                    continue

                count = counts_table[symbol]
                # Preserve this variant's 2 * count weights (standard method D
                # uses 2 * count - 1); update exclusion changes only learning.
                frequencies.append((symbol, 2 * count))

            # If all candidates are excluded, try a shorter n_order_context.
            if len(frequencies) == 0:
                continue

            # Each distinct byte contributes 1 to the ESCAPE weight.
            # Keep the existing exclusion rule: ESCAPE includes excluded bytes.
            escape_count = len(counts_table)
            frequencies.append((ESCAPE, escape_count))

            # Pause and give this table to the caller. A matching byte ends
            # the search; an ESCAPE resumes execution below for the next table.
            yield frequencies

            # After an ESCAPE, none of this n_order_context's bytes can be the target.
            for symbol in counts_table.keys():
                excluded_symbols.add(symbol)

        # If every n_order_context fails, use the order -1 model for unseen bytes:
        # give each remaining byte the same frequency of 1.
        frequencies = []
        for symbol in range(256):
            if symbol in excluded_symbols:
                continue

            frequencies.append((symbol, 1))

        yield frequencies

    def update(self, symbol):
        # Full update exclusion: insert the byte into contexts that escaped,
        # then increment the first context that already predicted it and stop.
        # Test membership before updating, so a new insertion does not stop us.
        longest_order = len(self.history)
        for order in range(longest_order, -1, -1):
            if order == 0:
                n_order_context = b""
            else:
                n_order_context = self.history[-order:]

            if n_order_context not in self.contexts:
                self.contexts[n_order_context] = {}

            counts_table = self.contexts[n_order_context]

            if symbol in counts_table:
                counts_table[symbol] += 1
                break
            counts_table[symbol] = 1

        # Order 0 needs no history; otherwise keep the last max_order bytes.
        if self.max_order > 0:
            current_byte = bytes([symbol])
            self.history = self.history + current_byte

            if len(self.history) > self.max_order:
                start_index = len(self.history) - self.max_order
                self.history = self.history[start_index:]


def arithmetic_compress(data: bytes, max_order=MAX_ORDER) -> bytes:
    # BWT runs before PPM; its output has the same length as the original data.
    data, primary_index = bwt_transform(data)
    # Header: b"BDU1", maximum order (uint8), size and primary index (uint64 each).
    # All integers are little-endian; the payload is packed MSB first.
    # Models start empty on both sides, so no frequency table is stored.
    output = bytearray(b"BDU1")
    output.extend(struct.pack("<BQQ", max_order, len(data), primary_index))
    if not data:
        return bytes(output)

    buffer = 0
    bits = 0
    pending = 0

    def write_bit(bit):
        nonlocal buffer, bits
        buffer = (buffer << 1) | bit
        bits += 1
        if bits == 8:
            output.append(buffer)
            buffer = 0
            bits = 0

    def write_with_pending(bit):
        nonlocal pending
        write_bit(bit)
        for _ in range(pending):
            write_bit(1 - bit)
        pending = 0

    low = 0
    high = MASK

    def encode_interval(lower, upper, total):
        nonlocal low, high, pending
        width = high - low + 1
        high = low + width * upper // total - 1
        low = low + width * lower // total

        while True:
            if (high & HALF) == 0:
                write_with_pending(0)
            elif (low & HALF) != 0:
                write_with_pending(1)
                low -= HALF
                high -= HALF
            elif (low & QUARTER) != 0 and (high & QUARTER) == 0:
                pending += 1
                low -= QUARTER
                high -= QUARTER
            else:
                break
            low <<= 1
            high = (high << 1) | 1

    model = PPMModel(max_order)
    for symbol in data:
        for frequencies in model.distributions():
            total = sum(count for _, count in frequencies)
            target = symbol if any(s == symbol for s, _ in frequencies) else ESCAPE
            lower = 0
            for candidate, count in frequencies:
                if candidate == target:
                    encode_interval(lower, lower + count, total)
                    break
                lower += count
            if target != ESCAPE:
                break
        model.update(symbol)

    # Final prefix; any unread bits beyond the payload are treated as zero.
    pending += 1
    write_with_pending(0 if low < QUARTER else 1)
    if bits:
        output.append(buffer << (8 - bits))
    return bytes(output)


def compress_file(source="austen.txt", destination="./BWT+PPMD+UE+arithmetic/compressed",
                  max_order=MAX_ORDER):
    with open(source, "rb") as fin:
        compressed = arithmetic_compress(fin.read(), max_order)
    with open(destination, "wb") as fout:
        fout.write(compressed)


if __name__ == "__main__":
    compress_file()
    print("Compression complete. Output written to ./BWT+PPMD+UE+arithmetic/compressed")
    print("size of compressed file:", os.path.getsize("./BWT+PPMD+UE+arithmetic/compressed") , "bytes")
