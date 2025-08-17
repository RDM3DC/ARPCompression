#!/usr/bin/env python3
import argparse, time, os, random
from pathlib import Path
import numpy as np
import pandas as pd
from pathtext.fec import crc16_ccitt, segment_bytes, rs_capacity_model, conceal_linear

def bsc_flip(data: bytes, p: float, rng) -> bytes:
    bits = bytearray(data)
    for i in range(len(bits)):
        b = bits[i]
        for k in range(8):
            if rng.random() < p:
                b ^= (1 << k)
        bits[i] = b
    return bytes(bits)

def bench(file_path: Path, p_list, mode: str, rs_t_bits: int, seg_size: int = 256, runs: int = 5):
    payload = file_path.read_bytes()
    segs = segment_bytes(payload, seg_size=seg_size)
    table = []
    for p in p_list:
        fer_count = 0
        t0 = time.time()
        for r in range(runs):
            rng = random.Random(1234 + r)
            ok = True
            prev_good = b''
            for idx, seg in enumerate(segs):
                flipped = bsc_flip(seg, p, rng)
                crc_ok = (crc16_ccitt(flipped) == crc16_ccitt(seg))
                if mode == "crc":
                    if not crc_ok:
                        ok = False
                elif mode == "rs":
                    # estimate bit errors
                    num_err_bits = sum(bin(a ^ b).count("1") for a, b in zip(seg, flipped))
                    if not rs_capacity_model(num_err_bits, rs_t_bits):
                        # try conceal
                        next_seg = segs[idx+1] if idx+1 < len(segs) else b''
                        recon = conceal_linear(prev_good, next_seg)
                        ok = False if not recon else ok
                    else:
                        prev_good = flipped
                else:
                    raise ValueError("mode must be 'crc' or 'rs'")
            if not ok:
                fer_count += 1
        decode_ms = (time.time() - t0) * 1000.0 / runs
        table.append({"mode": mode, "p": p, "FER": fer_count / runs, "decode_ms": decode_ms})
    return pd.DataFrame(table)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="Path to .atcp2/.atcp3 or any binary")
    ap.add_argument("--mode", choices=["crc","rs"], required=True)
    ap.add_argument("--p", type=float, nargs="+", default=[0.01,0.03,0.05])
    ap.add_argument("--seg_size", type=int, default=256)
    ap.add_argument("--rs_t_bits", type=int, default=16)  # ~correct up to 16 bit errors per segment (toy model)
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--out_csv", required=True)
    args = ap.parse_args()

    df = bench(Path(args.file), args.p, args.mode, args.rs_t_bits, args.seg_size, args.runs)
    Path(args.out_csv).write_text(df.to_csv(index=False), encoding="utf-8")
    print(f"[OK] wrote {args.out_csv}")

if __name__ == "__main__":
    main()
