
# Minimal adaptive arithmetic coder (integer, 32-bit range)
# Based on order-0 frequency model with 1-count initialization (Laplace).
from typing import List

TOP = (1<<32) - 1
HALF = 1<<31
QUARTER = 1<<30
THREEQ = 3<<30

class Model:
    def __init__(self, alphabet_size: int):
        self.n = alphabet_size
        self.freq = [1]*self.n  # Laplace smoothing
        self.cum = None
        self.total = 0
        self._rebuild()

    def _rebuild(self):
        self.cum = [0]*(self.n+1)
        s = 0
        for i in range(self.n):
            self.cum[i] = s
            s += self.freq[i]
        self.cum[self.n] = s
        self.total = s

    def update(self, sym: int):
        self.freq[sym] += 1
        # Rebuild occasionally to avoid big integers; here rebuild every time for simplicity
        self._rebuild()

class RangeEncoder:
    def __init__(self):
        self.low = 0
        self.high = TOP
        self.out = bytearray()
        self.underflow = 0

    def _put_byte(self, b: int):
        self.out.append(b & 0xFF)

    def _emit_bit_plus_underflow(self, bit):
        self._put_byte((bit & 1)*255)  # write 0x00 or 0xFF as a simple bit-packing surrogate
        # NOTE: For simplicity we emit full bytes 0x00/0xFF; this is not bit-optimal but demonstrates coding.
        # Underflow bits:
        inv = 0xFF if bit==0 else 0x00
        for _ in range(self.underflow):
            self._put_byte(inv)
        self.underflow = 0

    def encode_symbol(self, model: Model, sym: int):
        total = model.total
        low_count = model.cum[sym]
        high_count = model.cum[sym+1]

        range_ = self.high - self.low + 1
        self.high = self.low + (range_ * high_count // total) - 1
        self.low  = self.low + (range_ * low_count  // total)

        while True:
            if self.high < HALF:
                self._emit_bit_plus_underflow(0)
                self.low = self.low*2
                self.high = self.high*2 + 1
            elif self.low >= HALF:
                self._emit_bit_plus_underflow(1)
                self.low = (self.low - HALF)*2
                self.high = (self.high - HALF)*2 + 1
            elif self.low >= QUARTER and self.high < THREEQ:
                self.underflow += 1
                self.low = (self.low - QUARTER)*2
                self.high = (self.high - QUARTER)*2 + 1
            else:
                break

        model.update(sym)

    def finish(self):
        self.underflow += 1
        if self.low < QUARTER:
            self._emit_bit_plus_underflow(0)
        else:
            self._emit_bit_plus_underflow(1)
        return bytes(self.out)

class RangeDecoder:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0
        self.low = 0
        self.high = TOP
        # Read first byte as proxy for bit; since we wrote 0x00/0xFF per bit, treat 0xFF as 1
        self.code = 0
        # To keep consistent with our naive "bit" bytes, preload 32 bits worth
        for _ in range(4):
            self.code = (self.code<<8) | self._read_byte()

    def _read_byte(self):
        if self.pos >= len(self.data):
            return 0
        b = self.data[self.pos]
        self.pos += 1
        return b

    def _get_bit(self):
        # Convert 0x00 to 0, 0xFF to 1; any other value threshold at 128
        b = self._read_byte()
        return 1 if b >= 128 else 0

    def decode_symbol(self, model: Model) -> int:
        total = model.total
        range_ = self.high - self.low + 1
        # Map code into cumulative interval
        value = ((self.code - self.low + 1)*total - 1) // range_

        # Find symbol
        # Linear search (alphabet small): ok
        lo, hi = 0, model.n - 1
        sym = hi
        for s in range(model.n):
            if model.cum[s+1] > value >= model.cum[s]:
                sym = s
                break

        low_count = model.cum[sym]
        high_count = model.cum[sym+1]
        self.high = self.low + (range_ * high_count // total) - 1
        self.low  = self.low + (range_ * low_count  // total)

        while True:
            if self.high < HALF:
                # shift in a 0 bit
                self.code = ((self.code)*2) & TOP
                self.code |= self._get_bit()
                self.low = self.low*2
                self.high = self.high*2 + 1
            elif self.low >= HALF:
                self.code = ((self.code - HALF)*2) & TOP
                self.code |= self._get_bit()
                self.low = (self.low - HALF)*2
                self.high = (self.high - HALF)*2 + 1
            elif self.low >= QUARTER and self.high < THREEQ:
                self.code = ((self.code - QUARTER)*2) & TOP
                self.code |= self._get_bit()
                self.low = (self.low - QUARTER)*2
                self.high = (self.high - QUARTER)*2 + 1
            else:
                break

        model.update(sym)
        return sym
