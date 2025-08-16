
import math, json
from pathlib import Path
from .pathtext import encode_pathtext, to_svg

def sine_path(width=800, height=300, cycles=2.5, amp=40, n=200):
    y0 = height/2
    anchors = []
    for i in range(n):
        x = i*(width-40)/(n-1) + 20
        t = i/(n-1)
        y = y0 + amp*math.sin(2*math.pi*cycles*t)
        anchors.append([x,y])
    return anchors

def main():
    text = ("This is an ARPCompression experimental format: sentences flow along paths, "
            "not straight lines. Paths are stored as 2D anchors; text is ATC-compressed. "
            "Rendering uses SVG textPath.")
    path = {"id":"p0","anchors":sine_path() ,"alpha":0.2,"mu":0.01,"tau":0.0,"max_err":0.005}
    layout = [{"path":"p0","range":[0,len(text)],"spacing_px":14,"offset_px":0}]
    container = encode_pathtext(text, [path], layout, units="px", metadata={"demo":"sine"})
    out_svg = Path(__file__).resolve().parents[1] / "pathtext" / "demo.svg"
    to_svg(container, str(out_svg))
    out_json = Path(__file__).resolve().parents[1] / "pathtext" / "demo.atcp.json"
    out_json.write_text(json.dumps(container), encoding="utf-8")
    print("Wrote:", out_svg, "and", out_json)

if __name__ == "__main__":
    main()
