
"""
ATC-PATH CLI — encode
Usage:
  python -m pathtext.encode --text in.txt --anchors anchors.json --out out.atcp.json [--spacing 14] [--offset 0] [--pathid p0]

- in.txt: UTF-8 text
- anchors.json: {"paths": [{"id":"p0","anchors":[[x,y],...]}]}
"""
import json, argparse
from pathlib import Path
from .pathtext import encode_pathtext

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--anchors", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--spacing", type=int, default=14)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--pathid", default=None, help="Use this path id from anchors.json (default: first path)")
    args = ap.parse_args()

    text = Path(args.text).read_text(encoding="utf-8")
    anchors_obj = json.loads(Path(args.anchors).read_text(encoding="utf-8"))
    paths = anchors_obj["paths"]
    pid = args.pathid or paths[0]["id"]
    layout = [{"path": pid, "range": [0, len(text)], "spacing_px": args.spacing, "offset_px": args.offset}]
    container = encode_pathtext(text, paths, layout, units="px", metadata={"source_text": Path(args.text).name})
    Path(args.out).write_text(json.dumps(container), encoding="utf-8")
    print(f"Wrote {args.out}")

if __name__ == "__main__":
    main()
