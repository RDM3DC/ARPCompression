"""
ATC decoder: {"carriers": str, "style_b64": str} -> text
"""
import argparse, base64, json, sys
from typing import Dict, List
from .utils import unpack_style_bytes, parse_style_byte, CODE2PUNCT
ZERO_WIDTH = "\u200b"

def decode(pkg: Dict[str, str]) -> str:
    carriers = pkg["carriers"]
    style_b64 = pkg["style_b64"]
    style_bytes = unpack_style_bytes(base64.b64decode(style_b64))

    if len(carriers) != len(style_bytes):
        raise ValueError("Length mismatch: carriers vs style bytes")

    out_chars: List[str] = []

    for ch, b in zip(carriers, style_bytes):
        spaces_before, punct_code, cap_flag = parse_style_byte(b)

        # pre-insert spaces
        out_chars.append(" " * spaces_before)

        # apply capitalization and emit (skip zero-width carriers)
        if ch != ZERO_WIDTH:
            char = ch.upper() if cap_flag else ch
            out_chars.append(char)

        # append punctuation (postfix)
        punct = CODE2PUNCT.get(punct_code)
        if punct is not None:
            out_chars.append(punct)

    return "".join(out_chars)

def main():
    ap = argparse.ArgumentParser(description="Adaptive Text Compression (ATC) decoder")
    ap.add_argument("--in", dest="infile", type=str, default="-", help="Path to JSON package (or '-' for stdin)")
    args = ap.parse_args()

    if args.infile == "-" or args.infile is None:
        pkg = json.load(sys.stdin)
    else:
        with open(args.infile, "r", encoding="utf-8") as f:
            pkg = json.load(f)

    text = decode(pkg)
    print(text)

if __name__ == "__main__":
    main()
