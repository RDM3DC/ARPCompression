
"""
ATC CLI - compress
Usage:
  python -m atc.compress input.txt output.atc
"""
import sys, json
from pathlib import Path
from .codec_ac import pack as atc_pack

def main():
    if len(sys.argv) != 3:
        print("Usage: python -m atc.compress <input.txt> <output.atc>")
        sys.exit(1)
    inp = Path(sys.argv[1])
    outp = Path(sys.argv[2])
    text = inp.read_text(encoding="utf-8")
    obj = atc_pack(text)
    outp.write_text(json.dumps(obj), encoding="utf-8")
    print(f"Wrote {outp} ({outp.stat().st_size} bytes)")

if __name__ == "__main__":
    main()
