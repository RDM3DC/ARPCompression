
import argparse, json
from pathlib import Path
from .pathtext import encode_pathtext

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--anchors", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--spacing", type=int, default=14)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--pathid", default="p0")
    args = ap.parse_args()
    text = Path(args.text).read_text(encoding="utf-8")
    anchors = json.loads(Path(args.anchors).read_text(encoding="utf-8"))["paths"][0]["anchors"]
    container = encode_pathtext(text, [{"id":args.pathid,"anchors":anchors}], [{"path":args.pathid,"range":[0,len(text)],"spacing_px":args.spacing,"offset_px":args.offset}], "px", {})
    Path(args.out).write_text(json.dumps(container), encoding="utf-8")
    print("Wrote", args.out)

if __name__ == "__main__":
    main()
