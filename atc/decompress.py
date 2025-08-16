
"""
ATC CLI - decompress
Usage:
  python -m atc.decompress input.atc output.txt
"""
import sys, json
from pathlib import Path
from .codec_ac import unpack as atc_unpack

def main():
    if len(sys.argv) != 3:
        print("Usage: python -m atc.decompress <input.atc> <output.txt>")
        sys.exit(1)
    inp = Path(sys.argv[1])
    outp = Path(sys.argv[2])
    obj = json.loads(inp.read_text(encoding="utf-8"))
    text = atc_unpack(obj)
    outp.write_text(text, encoding="utf-8")
    print(f"Wrote {outp} ({outp.stat().st_size} bytes)")

if __name__ == "__main__":
    main()
