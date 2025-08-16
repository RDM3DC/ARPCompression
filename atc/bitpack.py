
from typing import Iterable, List

def pack_bits(values: Iterable[int], bits_per: int) -> bytes:
    buf = 0
    nbits = 0
    out = bytearray()
    for v in values:
        buf = (buf << bits_per) | (v & ((1<<bits_per)-1))
        nbits += bits_per
        while nbits >= 8:
            nbits -= 8
            out.append((buf >> nbits) & 0xFF)
            buf &= (1<<nbits)-1
    if nbits > 0:
        out.append((buf << (8-nbits)) & 0xFF)
    return bytes(out)

def unpack_bits(data: bytes, count: int, bits_per: int) -> List[int]:
    vals = []
    buf = 0
    nbits = 0
    it = iter(data)
    for b in it:
        buf = (buf << 8) | b
        nbits += 8
        while nbits >= bits_per and len(vals) < count:
            nbits -= bits_per
            vals.append((buf >> nbits) & ((1<<bits_per)-1))
            buf &= (1<<nbits)-1
        if len(vals) == count:
            break
    return vals
