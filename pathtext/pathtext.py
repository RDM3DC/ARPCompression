from pathlib import Path

"""
ATC-PATH: sentences following 2D paths (not straight lines)

Container (JSON):
{
  "format": "ATC-PATH-v1",
  "units": "px",
  "text_ac": {... ATC-AC2-v2 object ...},
  "paths": [
    {"id":"p0","anchors":[[x,y],...],"alpha":0.2,"mu":0.01,"tau":0.0,"max_err":0.005}
  ],
  "layout": [
    {"path":"p0","range":[0,120],"spacing_px":12,"offset_px":0}
  ],
  "metadata": {...}
}

- "paths[].anchors" are 2D points (pixel coordinates). A viewer can draw a polyline,
  or optionally fit splines. alpha/mu/tau/max_err are stored for provenance (CMC params).

- "layout[].range" selects a contiguous span of characters in the original text
  and places them along the given path with specified spacing (advance) and initial offset.

- "text_ac" is the arithmetic-coded ATC object (format ATC-AC2-v2).

This module provides:
- encode_pathtext(text, paths, layout) -> dict
- decode_text(container) -> str (round-trip to raw UTF-8)
- to_svg(container, out_path) -> writes a standalone SVG file that displays the text along paths.
"""
from typing import List, Dict, Tuple
import base64, json, math

from atc.codec_ac import pack as atc_pack, unpack as atc_unpack

def encode_pathtext(text: str, paths: List[Dict], layout: List[Dict], units: str="px", metadata: Dict=None) -> Dict:
    return {
        "format": "ATC-PATH-v1",
        "units": units,
        "text_ac": atc_pack(text),
        "paths": paths,
        "layout": layout,
        "metadata": metadata or {}
    }

def decode_text(container: Dict) -> str:
    assert container.get("format") == "ATC-PATH-v1"
    return atc_unpack(container["text_ac"])

def _path_to_svg_d(anchors: List[List[float]]) -> str:
    if not anchors: return ""
    d = [f"M {anchors[0][0]:.2f},{anchors[0][1]:.2f}"]
    for x,y in anchors[1:]:
        d.append(f"L {x:.2f},{y:.2f}")
    return " ".join(d)

def to_svg(container: Dict, out_path: str, width: int=800, height: int=300, font_family: str="sans-serif"):
    text = decode_text(container)
    # Build SVG with <path> elements + <text><textPath> segments
    svg_parts = []
    svg_parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
    svg_parts.append('<defs>')
    for p in container["paths"]:
        pid = p["id"]
        d = _path_to_svg_d(p["anchors"])
        svg_parts.append(f'<path id="{pid}" d="{d}" fill="none" stroke="#ccc" stroke-width="1"/>')
    svg_parts.append('</defs>')

    # Draw visible paths (light) and place text
    for p in container["paths"]:
        pid = p["id"]
        d = _path_to_svg_d(p["anchors"])
        svg_parts.append(f'<path d="{d}" fill="none" stroke="#e0e0e0" stroke-width="1"/>')

    for i, lay in enumerate(container["layout"]):
        pid = lay["path"]
        a, b = lay["range"]
        frag = (text[a:b]).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
        # spacing: we can approximate by letter-spacing; advanced layout would do glyph-by-glyph placement.
        spacing = lay.get("spacing_px", 12)
        svg_parts.append(f'<text font-family="{font_family}" font-size="{spacing}px" letter-spacing="0.5px">')
        svg_parts.append(f'  <textPath href="#{pid}" startOffset="{lay.get("offset_px",0)}">{frag}</textPath>')
        svg_parts.append('</text>')

    svg_parts.append('</svg>')
    Path(out_path).write_text("\n".join(svg_parts), encoding="utf-8")
    return out_path
