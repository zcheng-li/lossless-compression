"""Static arithmetic coding using global byte frequencies (no context model)."""

import os
import struct


STATE_BITS = 64
FULL_RANGE = 1 << STATE_BITS
HALF = FULL_RANGE >> 1
QUARTER = HALF >> 1
THREE_QUARTERS = QUARTER * 3
MASK = FULL_RANGE - 1



def arithmetic_compress(data: bytes) -> bytes:
    # P(symbol) = frequency[symbol] / total, fixed throughout encoding.
    frequencies = [0] * 256
    for symbol in data:
        frequencies[symbol] += 1
    total = len(data)
    if total >= QUARTER:
        raise ValueError("Input is too large for the 64-bit arithmetic coder")

    cumulative = [0]
    for frequency in frequencies:
        cumulative.append(cumulative[-1] + frequency)

    # Format (little-endian): b"ARI1", symbol count (uint16), then
    # (symbol: uint8, frequency: uint64) pairs in ascending symbol order.
    # The original byte count is the sum of the saved frequencies.
    # The remaining bytes are the arithmetic bitstream, MSB first, with
    # zero padding in the last byte. Empty input has no payload.
    
    # TODO: consider using a more compact representation
    output = bytearray(b"ARI1")
    output.extend(struct.pack("<H", sum(f > 0 for f in frequencies)))
    for symbol, frequency in enumerate(frequencies):
        if frequency:
            # TODO: consider using a more compact representation for small frequencies.
            output.extend(struct.pack("<BQ", symbol, frequency))
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
        # Underflow bits are the opposite of the next resolved bit.
        for _ in range(pending):
            write_bit(1 - bit)
        pending = 0

    low = 0
    high = MASK
    for symbol in data:
        # Narrow the inclusive interval using cumulative probabilities.
        width = high - low + 1
        high = low + width * cumulative[symbol + 1] // total - 1
        low = low + width * cumulative[symbol] // total

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

    # Choose a terminating prefix inside the final interval. A decoder
    # reads zero bits beyond the payload and stops after `total` symbols.
    pending += 1
    write_with_pending(0 if low < QUARTER else 1)
    if bits:
        output.append(buffer << (8 - bits))
    return bytes(output)


def compress_file(source="austen.txt", destination="./arithmatic/compressed"):
    with open(source, "rb") as fin:
        compressed = arithmetic_compress(fin.read())
    with open(destination, "wb") as fout:
        fout.write(compressed)


if __name__ == "__main__":
    compress_file()
    print("Compression complete. Output written to ./arithmatic/compressed")
    print("size of compressed file:", os.path.getsize("./arithmatic/compressed") / (1024 * 1024), "MB")
