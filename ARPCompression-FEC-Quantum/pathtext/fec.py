# Simple FEC helpers for PATHTEXT segments (prototype).
# - CRC16-CCITT for detection
# - RS-like capacity model: if bit errors <= t, "correct"; else fail
# - Geometric concealment: linear blend between last/next good segments

from typing import Tuple, List
import struct, zlib

# CRC16-CCITT (0x1021), initial 0xFFFF
def crc16_ccitt(data: bytes, poly=0x1021, init=0xFFFF) -> int:
    crc = init
    for b in data:
        crc ^= (b << 8) & 0xFFFF
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ poly) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc & 0xFFFF

def segment_bytes(payload: bytes, seg_size: int = 256) -> List[bytes]:
    return [payload[i:i+seg_size] for i in range(0, len(payload), seg_size)]

def rs_capacity_model(num_bits_flipped: int, t_correctable_bits: int) -> bool:
    # True if correctable
    return num_bits_flipped <= t_correctable_bits

def conceal_linear(prev_seg: bytes, next_seg: bytes) -> bytes:
    # Byte-wise average (prototype)
    if not prev_seg and not next_seg:
        return b''
    if not prev_seg: return next_seg
    if not next_seg: return prev_seg
    m = min(len(prev_seg), len(next_seg))
    out = bytearray(m)
    for i in range(m):
        out[i] = (prev_seg[i] + next_seg[i]) // 2
    return bytes(out)
