"""Decode the static arithmetic format using its saved global frequencies."""

from bisect import bisect_right
import struct


STATE_BITS = 64
FULL_RANGE = 1 << STATE_BITS
HALF = FULL_RANGE >> 1
QUARTER = HALF >> 1
MASK = FULL_RANGE - 1


def arithmetic_decompress(data: bytes) -> bytes:
    symbol_count = struct.unpack_from("<H", data, 4)[0]
    payload_start = 6 + 9 * symbol_count
    if symbol_count > 256 or len(data) < payload_start:
        raise ValueError("Invalid or incomplete frequency table")

    frequencies = [0] * 256
    previous_symbol = -1
    for position in range(6, payload_start, 9):
        symbol, frequency = struct.unpack_from("<BQ", data, position)
        if symbol <= previous_symbol or frequency == 0:
            raise ValueError("Invalid frequency table entry")
        frequencies[symbol] = frequency
        previous_symbol = symbol

    cumulative = [0]
    for frequency in frequencies:
        cumulative.append(cumulative[-1] + frequency)
    total = cumulative[-1]
    if total == 0:
        return b""

    bit_position = payload_start * 8
    bit_limit = len(data) * 8

    def read_bit():
        nonlocal bit_position
        # Read MSB first; the encoder's final prefix is extended with zeros.
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

    output = bytearray()
    for _ in range(total):
        # Map value back to the cumulative-frequency scale. The +1/-1
        # account for the inclusive integer bounds used by the encoder.
        width = high - low + 1
        scaled = ((value - low + 1) * total - 1) // width
        symbol = bisect_right(cumulative, scaled) - 1
        output.append(symbol)

        high = low + width * cumulative[symbol + 1] // total - 1
        low = low + width * cumulative[symbol] // total

        # Mirror E1/E2/E3 and transform value along with the interval.
        # No pending counter is needed: read the emitted bits directly.
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

    return bytes(output)


def decompress_file(source="compressed", destination="out.txt"):
    with open(source, "rb") as fin:
        decompressed = arithmetic_decompress(fin.read())
    with open(destination, "wb") as fout:
        fout.write(decompressed)


decompress_file()
