
from typing import List, Dict
from pathlib import Path

def encode_pathtext(text: str, paths: List[Dict], layout: List[Dict], units: str="px", metadata: Dict=None) -> Dict:
    return {
        "format": "ATC-PATH-v1",
        "units": units,
        "text_raw": text,
        "paths": paths,
        "layout": layout,
        "metadata": metadata or {}
    }

def decode_text(container: Dict) -> str:
    return container.get("text_raw","")

def _path_to_svg_d(anchors: List[List[float]]) -> str:
    if not anchors: return ""
    out = [f"M {anchors[0][0]},{anchors[0][1]}"]
    for x,y in anchors[1:]:
        out.append(f"L {x},{y}")
    return " ".join(out)

def to_svg(container: Dict, out_path: str, width: int=800, height: int=300, font_family: str="sans-serif"):
    text = decode_text(container)
    parts = []
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
    parts.append('<defs>')
    for p in container["paths"]:
        d = _path_to_svg_d(p.get("anchors", []))
        parts.append(f'<path id="{p.get("id","p0")}" d="{d}" fill="none" stroke="#ccc" stroke-width="1"/>')
    parts.append('</defs>')
    for p in container["paths"]:
        d = _path_to_svg_d(p.get("anchors", []))
        parts.append(f'<path d="{d}" fill="none" stroke="#e0e0e0" stroke-width="1"/>')
    for lay in container["layout"]:
        frag = text[lay["range"][0]:lay["range"][1]].replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
        parts.append(f'<text font-family="{font_family}" font-size="{lay.get("spacing_px",14)}px" letter-spacing="0.5px">')
        parts.append(f'  <textPath href="#{lay["path"]}" startOffset="{lay.get("offset_px",0)}">{frag}</textPath>')
        parts.append('</text>')
    parts.append('</svg>')
    Path(out_path).write_text("\n".join(parts), encoding="utf-8")
    return out_path
