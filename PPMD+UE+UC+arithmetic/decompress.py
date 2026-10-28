"""Standalone decoder for the PPM + update exclusion + arithmetic PDU1 format."""

import struct

STATE_BITS = 64
FULL_RANGE = 1 << STATE_BITS
HALF = FULL_RANGE >> 1
QUARTER = HALF >> 1
MASK = FULL_RANGE - 1
MAX_ORDER = 5
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
            frequencies = [(symbol, 2 * count) for symbol, count in sorted(counts.items())
                           if symbol not in excluded]
            if not frequencies:
                continue
            # Preserve the encoder's 2 * count weights; ESCAPE gets one per
            # distinct symbol, including those removed by exclusion.
            frequencies.append((ESCAPE, len(counts)))
            yield frequencies
            excluded.update(counts)

        # Order -1: all remaining byte values have equal probability.
        yield [(symbol, 1) for symbol in range(256) if symbol not in excluded]

    def update(self, symbol):
        # Insert into escaped contexts, increment the first predicting one,
        # then exclude every lower order from this update.
        for order in range(len(self.history), -1, -1):
            context = self.history[-order:] if order else b""
            counts = self.contexts.setdefault(context, {})
            if symbol in counts:
                counts[symbol] += 1
                break
            counts[symbol] = 1
        if self.max_order:
            self.history = (self.history + bytes([symbol]))[-self.max_order:]


def arithmetic_decompress(data):
    max_order, original_size = struct.unpack_from("<BQ", data, 4)
    if original_size == 0:
        return b""

    bit_position = 13 * 8
    bit_limit = len(data) * 8

    def read_bit():
        nonlocal bit_position
        if bit_position < bit_limit:
            bit = (data[bit_position // 8] >> (7 - bit_position % 8)) & 1
        else:
            bit = 0
        bit_position += 1
        return bit

    low = 0
    high = MASK
    value = 0
    for _ in range(STATE_BITS):
        value = (value << 1) | read_bit()

    def decode_symbol(frequencies):
        nonlocal low, high, value
        total = sum(count for _, count in frequencies)
        width = high - low + 1
        scaled = ((value - low + 1) * total - 1) // width
        lower = 0
        for symbol, count in frequencies:
            if scaled < lower + count:
                break
            lower += count

        high = low + width * (lower + count) // total - 1
        low = low + width * lower // total
        while True:
            if (high & HALF) == 0:
                pass
            elif (low & HALF) != 0:
                low -= HALF
                high -= HALF
                value -= HALF
            elif (low & QUARTER) != 0 and (high & QUARTER) == 0:
                low -= QUARTER
                high -= QUARTER
                value -= QUARTER
            else:
                break
            low <<= 1
            high = (high << 1) | 1
            value = (value << 1) | read_bit()
        return symbol

    model = PPMModel(max_order)
    output = bytearray()
    for _ in range(original_size):
        for frequencies in model.distributions():
            symbol = decode_symbol(frequencies)
            if symbol != ESCAPE:
                break
        output.append(symbol)
        model.update(symbol)
    return bytes(output)


def decompress_file(source="compressed", destination="out.txt"):
    with open(source, "rb") as fin:
        decompressed = arithmetic_decompress(fin.read())
    with open(destination, "wb") as fout:
        fout.write(decompressed)


if __name__ == "__main__":
    decompress_file()
