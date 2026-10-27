"""PPM-C with exclusion and a 64-bit arithmetic coder.

Model reference: Cleary and Teahan, Unbounded Length Contexts for PPM,
https://www.cs.ucf.edu/courses/cap5015/Cleary.pdf (PPM introduction).
"""

import os
import struct


STATE_BITS = 64
FULL_RANGE = 1 << STATE_BITS
HALF = FULL_RANGE >> 1
QUARTER = HALF >> 1
MASK = FULL_RANGE - 1
MAX_ORDER = 4
ESCAPE = 256


class PPMModel:
    def __init__(self, max_order=MAX_ORDER):
        self.max_order = max_order
        self.history = b""
        self.contexts = {}

    def distributions(self):
        # Start with the longest context, shortening it after each ESCAPE.
        excluded = set()
        for order in range(len(self.history), -1, -1):
            context = self.history[-order:] if order else b""
            counts = self.contexts.get(context, {})
            frequencies = [(symbol, count) for symbol, count in sorted(counts.items())
                           if symbol not in excluded]
            if not frequencies:
                continue
            # Method C: ESCAPE gets one count per distinct context symbol.
            # Exclusion removes higher-order symbols from the lower model.
            frequencies.append((ESCAPE, len(counts)))
            yield frequencies
            excluded.update(counts)

        # Order -1: all remaining byte values have equal probability.
        yield [(symbol, 1) for symbol in range(256) if symbol not in excluded]

    def update(self, symbol):
        # Learn only after encoding/decoding the byte, at every context order.
        for order in range(len(self.history) + 1):
            context = self.history[-order:] if order else b""
            counts = self.contexts.setdefault(context, {})
            counts[symbol] = counts.get(symbol, 0) + 1
        if self.max_order:
            self.history = (self.history + bytes([symbol]))[-self.max_order:]


def arithmetic_compress(data: bytes, max_order=MAX_ORDER) -> bytes:
    # Header: b"PAR1", maximum context order (uint8), original size (uint64).
    # All integers are little-endian; the payload is packed MSB first.
    # Models start empty on both sides, so no frequency table is stored.
    output = bytearray(b"PAR1")
    output.extend(struct.pack("<BQ", max_order, len(data)))
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


def compress_file(source="austen.txt", destination="./PPM+arithmetic/compressed",
                  max_order=MAX_ORDER):
    with open(source, "rb") as fin:
        compressed = arithmetic_compress(fin.read(), max_order)
    with open(destination, "wb") as fout:
        fout.write(compressed)


if __name__ == "__main__":
    compress_file()
    print("Compression complete. Output written to ./PPM+arithmetic/compressed")
    print("size of compressed file:", os.path.getsize("./PPM+arithmetic/compressed") / (1024 * 1024), "MB")
