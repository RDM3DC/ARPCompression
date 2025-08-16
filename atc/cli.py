
import argparse, json, sys
from .encoder import encode as _encode
from .decoder import decode as _decode

def encode_main(argv=None):
    ap = argparse.ArgumentParser(description="ATC encoder (carriers + style bytes)")
    ap.add_argument("--text", type=str, help="Input text to encode")
    ap.add_argument("--infile", type=str, help="Read text from file (mutually exclusive with --text)")
    ap.add_argument("--out", type=str, default="-", help="JSON output path (or '-' for stdout)")
    args = ap.parse_args(argv)

    if (args.text is None) == (args.infile is None):
        print("Provide exactly one of --text or --infile", file=sys.stderr)
        sys.exit(1)

    text = args.text if args.text is not None else open(args.infile, "r", encoding="utf-8").read()
    pkg = _encode(text)
    out_json = json.dumps(pkg, ensure_ascii=False, indent=2)
    if args.out == "-" or args.out is None:
        print(out_json)
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out_json)

def decode_main(argv=None):
    ap = argparse.ArgumentParser(description="ATC decoder (JSON package to text)")
    ap.add_argument("--in", dest="infile", type=str, default="-", help="JSON input path (or '-' for stdin)")
    args = ap.parse_args(argv)
    if args.infile == "-" or args.infile is None:
        pkg = json.load(sys.stdin)
    else:
        with open(args.infile, "r", encoding="utf-8") as f:
            pkg = json.load(f)
    text = _decode(pkg)
    print(text)
