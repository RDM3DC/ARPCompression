
import os, sys, time, gzip, io, base64, json, csv, argparse
from pathlib import Path

# Optional imports
try:
    import brotli
except Exception:
    brotli = None

try:
    import zstandard as zstd
except Exception:
    zstd = None

# Repo imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atc.codec_simple import pack as atc_pack_z, unpack as atc_unpack_z
from atc.codec_ac import pack as atc_pack_ac, unpack as atc_unpack_ac

def size_utf8(b: bytes) -> int:
    return len(b)

def gzip_compress(b: bytes) -> bytes:
    return gzip.compress(b, compresslevel=9)

def gzip_decompress(b: bytes) -> bytes:
    return gzip.decompress(b)

def brotli_compress(b: bytes) -> bytes:
    if brotli is None:
        return None
    return brotli.compress(b)

def brotli_decompress(b: bytes) -> bytes:
    return brotli.decompress(b)

def zstd_compress(b: bytes, level: int = 10) -> bytes:
    if zstd is None:
        return None
    cctx = zstd.ZstdCompressor(level=level)
    return cctx.compress(b)

def zstd_decompress(b: bytes) -> bytes:
    dctx = zstd.ZstdDecompressor()
    return dctx.decompress(b)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", type=str, required=True, help="Folder with .txt files")
    ap.add_argument("--out_csv", type=str, default="bench_results.csv")
    args = ap.parse_args()
    folder = Path(args.folder)
    rows = []
    for path in sorted(folder.glob("*.txt")):
        raw = path.read_bytes()
        name = path.name

        # UTF-8 size baseline
        rows.append({"file": name, "codec": "utf8", "size": len(raw), "enc_ms": 0.0, "dec_ms": 0.0, "ok": True})

        # gzip
        t0 = time.perf_counter(); gz = gzip_compress(raw); t1 = time.perf_counter()
        t2 = time.perf_counter(); raw_gz = gzip_decompress(gz); t3 = time.perf_counter()
        rows.append({"file": name, "codec": "gzip", "size": len(gz), "enc_ms": (t1-t0)*1000, "dec_ms": (t3-t2)*1000, "ok": raw_gz == raw})

        # brotli (if available)
        if brotli is not None:
            t0 = time.perf_counter(); br = brotli_compress(raw); t1 = time.perf_counter()
            t2 = time.perf_counter(); raw_br = brotli_decompress(br); t3 = time.perf_counter()
            rows.append({"file": name, "codec": "brotli", "size": len(br), "enc_ms": (t1-t0)*1000, "dec_ms": (t3-t2)*1000, "ok": raw_br == raw})

        # zstd (if available)
        if zstd is not None:
            t0 = time.perf_counter(); zs = zstd_compress(raw, level=10); t1 = time.perf_counter()
            t2 = time.perf_counter(); raw_zs = zstd_decompress(zs); t3 = time.perf_counter()
            rows.append({"file": name, "codec": "zstd", "size": len(zs), "enc_ms": (t1-t0)*1000, "dec_ms": (t3-t2)*1000, "ok": raw_zs == raw})

        # ATC (bitpack+zlib): store JSON blob for size and decode
        t0 = time.perf_counter()
        obj_z = atc_pack_z(raw.decode("utf-8"))
        blob_z = json.dumps(obj_z).encode("utf-8")
        t1 = time.perf_counter()
        t2 = time.perf_counter()
        text_z = atc_unpack_z(obj_z)
        raw_atc_z = text_z.encode("utf-8")
        t3 = time.perf_counter()
        rows.append({"file": name, "codec": "atc_bitpack", "size": len(blob_z), "enc_ms": (t1-t0)*1000, "dec_ms": (t3-t2)*1000, "ok": raw_atc_z == raw})

        # ATC (arithmetic): store JSON blob for size and decode
        t0 = time.perf_counter()
        obj_ac = atc_pack_ac(raw.decode("utf-8"))
        blob_ac = json.dumps(obj_ac).encode("utf-8")
        t1 = time.perf_counter()
        t2 = time.perf_counter()
        text_ac = atc_unpack_ac(obj_ac)
        raw_atc_ac = text_ac.encode("utf-8")
        t3 = time.perf_counter()
        rows.append({"file": name, "codec": "atc_arith", "size": len(blob_ac), "enc_ms": (t1-t0)*1000, "dec_ms": (t3-t2)*1000, "ok": raw_atc_ac == raw})

    out_csv = Path(args.out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file","codec","size","enc_ms","dec_ms","ok"])
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {out_csv}")

if __name__ == "__main__":
    main()
