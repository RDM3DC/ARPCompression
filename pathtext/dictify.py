
import json, argparse
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp"); ap.add_argument("out")
    ap.add_argument("--repeat", type=int, default=2)
    args = ap.parse_args()
    obj = json.loads(Path(args.inp).read_text(encoding="utf-8"))
    paths = obj.get("paths", [])
    if not paths:
        Path(args.out).write_text(json.dumps(obj), encoding="utf-8"); return
    base = paths[0].get("anchors_cmc", {}).get("anchors", paths[0].get("anchors", []))
    obj["glyph_table"] = [{"id":"g0", "anchors": base}]
    ops = []
    for i in range(args.repeat):
        if i == 0:
            ops.append({"op":"PLACE_FULL","tx":0.0,"ty":0.0,"theta_deg":0.0,"scale":1.0,"glyph_idx":0})
        else:
            ops.append({"op":"PLACE_DELTA","dtx":200.0,"dty":0.0,"dtheta_deg":0.0,"dlog2s":0.0})
    obj["paths"] = [{"id":"p0","glyph_ops": ops, "max_err": paths[0].get("max_err",0.0)}]
    if obj.get("layout"):
        rng = obj["layout"][0]["range"]
        obj["layout"] = [{"path":"p0","range":rng,"spacing_px":obj["layout"][0].get("spacing_px",14),"offset_px":0}]
    Path(args.out).write_text(json.dumps(obj), encoding="utf-8")
    print(f"Wrote {args.out}")
if __name__ == "__main__":
    main()
