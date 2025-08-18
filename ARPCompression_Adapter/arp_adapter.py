

"""
ARPCompression integration adapter

- Safe path for log(p): fixed-point (2**44), delta, zigzag-varint, zlib
- Optional ARPCompression.gpuc for large arrays (H(t), t-grids) where slight loss is OK

Usage (Python):
    from arp_adapter import save_logp_vzc, load_logp_vzc
    from arp_adapter import gpuc_quantize_npz, gpuc_dequantize_npz

CLI:
    python -m arp_adapter.compress_logp  --in data/shards/logp_shard0001.npy --out data/shards_vzc/logp_shard0001
    python -m arp_adapter.decompress_logp --in data/shards_vzc/logp_shard0001
    python -m arp_adapter.gpuc_quantize   --in outputs_phase16/H.npy --bits 12 --out outputs_phase16/H_q.npz
    python -m arp_adapter.gpuc_dequantize --in outputs_phase16/H_q.npz --out outputs_phase16/H_restored.npy
"""
from __future__ import annotations
import io, os, json, zlib, struct
import numpy as np

# ---------- fixed-point delta+varint (numerically safe for log(p)) ----------
def _zigzag_encode(n: int) -> int:
    return (n << 1) ^ (n >> 63)
def _zigzag_decode(z: int) -> int:
    return (z >> 1) ^ -(z & 1)

def _varint_write(buf: io.BytesIO, n: int) -> None:
    while True:
        to_write = n & 0x7F
        n >>= 7
        if n:
            buf.write(bytes([to_write | 0x80]))
        else:
            buf.write(bytes([to_write]))
            break

def _varint_read(mv: memoryview, pos: int):
    shift = 0
    result = 0
    while True:
        b = mv[pos]; pos += 1
        result |= (b & 0x7F) << shift
        if (b & 0x80) == 0:
            break
        shift += 7
    return result, pos

def save_logp_vzc(logp: np.ndarray, out_stem: str, scale_bits: int = 44, level: int = 6):
    assert logp.dtype == np.float64
    S = 1 << scale_bits
    q = np.rint(logp * S).astype(np.int64, copy=False)
    # delta
    d0 = int(q[0])
    d = np.empty_like(q)
    d[0] = d0
    d[1:] = q[1:] - q[:-1]
    # pack
    buf = io.BytesIO()
    for val in d.tolist():
        _varint_write(buf, _zigzag_encode(int(val)))
    raw = buf.getvalue()
    payload = zlib.compress(raw, level=level)
    meta = {
        "codec": "fp-delta-varint-zlib",
        "scale_bits": scale_bits,
        "count": int(q.size),
        "dtype": "float64",
        "endianness": "le",
        "zlib_level": level,
        "first_q": d0,
    }
    os.makedirs(os.path.dirname(out_stem), exist_ok=True)
    with open(out_stem + ".vzc", "wb") as f: f.write(payload)
    with open(out_stem + ".json", "w") as f: json.dump(meta, f, indent=2)
    return {"bytes": len(payload), "count": int(q.size)}

def load_logp_vzc(stem_or_vzc_path: str) -> np.ndarray:
    if stem_or_vzc_path.endswith(".vzc"):
        stem = stem_or_vzc_path[:-4]
    else:
        stem = stem_or_vzc_path
    with open(stem + ".json","r") as f: meta = json.load(f)
    with open(stem + ".vzc","rb") as f: payload = f.read()
    S = 1 << int(meta["scale_bits"])
    raw = zlib.decompress(payload)
    mv = memoryview(raw)
    pos = 0
    n = int(meta["count"])
    q = np.empty(n, dtype=np.int64)
    acc = 0
    for i in range(n):
        z, pos = _varint_read(mv, pos)
        d = _zigzag_decode(z)
        acc += d
        q[i] = acc
    logp = q.astype(np.float64) / float(S)
    return logp

# ---------- optional: ARPCompression.gpuc for big arrays (lossy) ----------
def _have_gpuc():
    try:
        from gpuc.quant import quantize, dequantize  # noqa: F401
        return True
    except Exception:
        return False

def gpuc_quantize_npz(arr_path: str, out_path: str, bits: int = 12):
    """
    Quantize arbitrary array (e.g., H(t)) using ARPCompression.gpuc.
    Only for arrays where small loss is acceptable.
    """
    # lazy import to avoid hard dependency
    from gpuc.quant import quantize
    import numpy as np
    arr = np.load(arr_path)
    pkt = quantize(arr, bits=bits)   # returns dict
    np.savez_compressed(out_path, **pkt)
    return {"out": out_path, "bits": bits, "shape": tuple(arr.shape)}

def gpuc_dequantize_npz(npz_path: str, out_path: str):
    from gpuc.quant import dequantize
    import numpy as np
    data = dict(np.load(npz_path))
    arr = dequantize(data)
    np.save(out_path, arr)
    return {"out": out_path, "shape": tuple(arr.shape)}

# ---------- CLIs ----------
def _cli_compress_logp():
    import argparse, numpy as np
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="out", required=True, help="output stem (no extension)")
    ap.add_argument("--scale_bits", type=int, default=44)
    ap.add_argument("--zlib_level", type=int, default=6)
    args = ap.parse_args()
    x = np.load(args.inp).astype(np.float64)
    info = save_logp_vzc(x, args.out, scale_bits=args.scale_bits, level=args.zlib_level)
    print("compressed:", info)

def _cli_decompress_logp():
    import argparse, numpy as np, os
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="stem", required=True, help="stem or .vzc path")
    ap.add_argument("--out", dest="out", default=None)
    args = ap.parse_args()
    x = load_logp_vzc(args.stem)
    if args.out is None:
        print("shape:", x.shape, "dtype:", x.dtype, "first/last:", x[0], x[-1])
    else:
        np.save(args.out, x); print("wrote", args.out)

def _cli_gpuc_quant():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="out", required=True)
    ap.add_argument("--bits", type=int, default=12)
    args = ap.parse_args()
    info = gpuc_quantize_npz(args.inp, args.out, bits=args.bits)
    print("quantized:", info)

def _cli_gpuc_dequant():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="out", required=True)
    args = ap.parse_args()
    info = gpuc_dequantize_npz(args.inp, args.out)
    print("dequantized:", info)

if __name__ == "__main__":
    import sys
    cmd = os.path.basename(sys.argv[0])
    # support: python -m arp_adapter.<subcommand>

