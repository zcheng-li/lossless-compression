"""PPM with method-D-style weights, full update exclusion and arithmetic coding.

Model reference: W. J. Teahan, Probability estimation for PPM,
https://cotty.16x16.com/compress/peppm.htm (update exclusions).
"""

import os


STATE_BITS = 64
FULL_RANGE = 1 << STATE_BITS
HALF = FULL_RANGE >> 1
QUARTER = HALF >> 1
MASK = FULL_RANGE - 1
MAX_ORDER = 5
ESCAPE = 256

# update 1:
# 20:8.6 : 616798 bytes best: (616798 + 5315) / 2664245 = 23.3504%
# update 2:
# Compact header + decoder: (616789 + 4910) / 2664245 = 23.3349%



class PPMModel:
    def __init__(self):
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
                # Tuned symbol weight; the decoder must use the same weights.
                frequencies.append((symbol, 200 * count))

            # If all candidates are excluded, try a shorter n_order_context.
            if len(frequencies) == 0:
                continue

            # Each distinct byte contributes 86 to the ESCAPE weight.
            # Keep the existing exclusion rule: ESCAPE includes excluded bytes.
            escape_count = len(counts_table)
            frequencies.append((ESCAPE, 86 * escape_count))
            # update 1:
            # 20:11 : 617965 bytes
            # 20:10 : 617220 bytes
            # 20:9.5 : 616975 bytes
            # 20:9 : 616831 bytes
            # 20:8.8 : 616805 bytes
            # 20:8.7 : 616799 bytes
            # 20:8.6 : 616798 bytes best: (616789 + 4910) / 2664245 = 23.3349%
            # 20:8.5 : 616802 bytes
            # 20:8 : 616906 bytes

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

        # This format always uses order 5.
        self.history = (self.history + bytes([symbol]))[-MAX_ORDER:]


def arithmetic_compress(data: bytes) -> bytes:
    # Header: original size (uint32, little-endian); order is fixed at 5.
    # The payload is packed MSB first.
    # Models start empty on both sides, so no frequency table is stored.
    output = bytearray(len(data).to_bytes(4, "little"))
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

    model = PPMModel()
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


def compress_file(source="austen.txt", destination=None):
    if destination is None:
        destination = os.path.join(os.path.dirname(__file__), "compressed")
    with open(source, "rb") as fin:
        compressed = arithmetic_compress(fin.read())
    with open(destination, "wb") as fout:
        fout.write(compressed)


if __name__ == "__main__":
    output_path = os.path.join(os.path.dirname(__file__), "compressed")
    compress_file(destination=output_path)
    print("Compression complete. Output written to", output_path)
    print("size of compressed file:", os.path.getsize(output_path), "bytes")
