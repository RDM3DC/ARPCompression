
import json, argparse
from pathlib import Path
from .path_compress import compress_anchors, compress_anchors_topk

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("out")
    ap.add_argument("--eps", type=float, default=None)
    ap.add_argument("--target_k", type=int, default=None)
    args = ap.parse_args()
    if args.eps is None and args.target_k is None:
        raise SystemExit("Specify --eps or --target_k")
    obj = json.loads(Path(args.inp).read_text(encoding="utf-8"))
    for p in obj.get("paths", []):
        if args.target_k is not None:
            comp = compress_anchors_topk(p.get("anchors", []), args.target_k)
        else:
            comp = compress_anchors(p.get("anchors", []), args.eps)
        p["anchors_cmc"] = comp
        p["max_err"] = max(p.get("max_err", 0.0), comp["max_err_px"])
    Path(args.out).write_text(json.dumps(obj), encoding="utf-8")
    print(f"Wrote {args.out}")
    for p in obj.get("paths", []):
        c = p.get("anchors_cmc", {})
        if c:
            if c.get("method") == "topk":
                print(f'Path {p.get("id")} : {c.get("orig_points")} -> {c.get("new_points")} points (Top-K={c.get("k")}), max_err={c.get("max_err_px"):.2f}px')
            else:
                print(f'Path {p.get("id")} : {c.get("orig_points")} -> {c.get("new_points")} points (RDP eps={c.get("eps_px")}), max_err={c.get("max_err_px"):.2f}px')

if __name__ == "__main__":
    main()
