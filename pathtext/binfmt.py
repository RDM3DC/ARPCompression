
import struct, base64, json
from pathlib import Path
from typing import List, Dict, Tuple

MAGIC = b"ATCP2\x01"
GSEC  = b"GSEC"

OP_PLACE_FULL = 1
OP_PLACE_DELTA = 2
OP_RESYNC = 3

def _pack_anchors_int16(anchors: List[List[float]]):
    import struct, math
    if not anchors:
        return (0, b"")
    xi = [int(round(p[0])) for p in anchors]
    yi = [int(round(p[1])) for p in anchors]
    x0, y0 = xi[0], yi[0]
    buf = bytearray()
    buf += struct.pack("<ii", x0, y0)
    px, py = x0, y0
    for i in range(1, len(xi)):
        dx = xi[i]-px; dy = yi[i]-py
        dx = max(-32768, min(32767, dx))
        dy = max(-32768, min(32767, dy))
        buf += struct.pack("<hh", dx, dy)
        px += dx; py += dy
    return (len(xi), bytes(buf))

def pack_binary(container: Dict) -> bytes:
    assert container.get("format") == "ATC-PATH-v1"
    text = container.get("text_raw","")
    text_bytes = text.encode("utf-8")
    n = len(text_bytes)

    paths = container.get("paths", [])
    layout = container.get("layout", [])
    glyph_table = container.get("glyph_table", [])

    chunks = [MAGIC]
    header = struct.pack("<I H I H H", n, 0, len(text_bytes), len(paths), len(layout))
    chunks.append(header)
    chunks.append(b"")  # no ext
    chunks.append(text_bytes)

    if glyph_table:
        chunks.append(GSEC)
        chunks.append(struct.pack("<H", len(glyph_table)))
        for g in glyph_table:
            gid = g.get("id","")
            anchors = g.get("anchors", [])
            count, data = _pack_anchors_int16(anchors)
            gid_b = gid.encode("utf-8")
            chunks.append(struct.pack("<H", len(gid_b)))
            chunks.append(gid_b)
            chunks.append(struct.pack("<I", count))
            chunks.append(data)

    for p in paths:
        if "glyph_ops" in p:
            ops = p["glyph_ops"]
            eps = float(p.get("max_err", 0.0))
            obuf = bytearray()
            for op in ops:
                code = op.get("op")
                if code == "PLACE_FULL":
                    tx,ty = float(op["tx"]), float(op["ty"])
                    theta = float(op.get("theta_deg", 0.0))
                    scale = float(op.get("scale", 1.0))
                    glyph_idx = int(op["glyph_idx"])
                    obuf += struct.pack("<B f f f f H", OP_PLACE_FULL, tx,ty,theta,scale,glyph_idx)
                elif code == "PLACE_DELTA":
                    dtx,dty,dtheta,dlogs = float(op.get("dtx",0.0)), float(op.get("dty",0.0)), float(op.get("dtheta_deg",0.0)), float(op.get("dlog2s",0.0))
                    obuf += struct.pack("<B f f f f", OP_PLACE_DELTA, dtx,dty,dtheta,dlogs)
                elif code == "RESYNC":
                    obuf += struct.pack("<B", OP_RESYNC)
            chunks.append(struct.pack("<H f I", 2, eps, len(obuf)))
            chunks.append(bytes(obuf))
        else:
            anchors = p.get("anchors_cmc", {}).get("anchors", p.get("anchors", []))
            count, data = _pack_anchors_int16(anchors)
            eps = float(p.get("max_err", 0.0))
            chunks.append(struct.pack("<H f I", 0, eps, count))
            chunks.append(data)

    id2idx = {p.get("id", f"p{i}"): i for i, p in enumerate(paths)}
    for lay in layout:
        pid = lay["path"]
        idx = id2idx[pid]
        a, b = lay["range"]
        spacing = float(lay.get("spacing_px", 14))
        offset = float(lay.get("offset_px", 0))
        chunks.append(struct.pack("<H I I f f", idx, a, b, spacing, offset))

    return b"".join(chunks)

def _reconstruct_from_glyph_ops(ops_bytes: bytes, glyph_pts: List[List[Tuple[int,int]]]) -> List[Tuple[int,int]]:
    import struct, math
    pts = []
    off = 0
    tx=ty=0.0; theta=0.0; scale=1.0; current_gid=0
    def apply(gid, tx,ty,theta,scale):
        nonlocal pts
        rad = math.radians(theta)
        cos = math.cos(rad); sin = math.sin(rad)
        for (x,y) in glyph_pts[gid]:
            xr = scale*(cos*x - sin*y) + tx
            yr = scale*(sin*x + cos*y) + ty
            pts.append((int(round(xr)), int(round(yr))))
    while off < len(ops_bytes):
        code = ops_bytes[off]; off += 1
        if code == 1:
            tx,ty,theta,scale,gid = struct.unpack_from("<f f f f H", ops_bytes, off); off += struct.calcsize("<f f f f H")
            current_gid = gid
            apply(gid, tx,ty,theta,scale)
        elif code == 2:
            dtx,dty,dtheta,dlogs = struct.unpack_from("<f f f f", ops_bytes, off); off += struct.calcsize("<f f f f")
            tx += dtx; ty += dty; theta += dtheta; scale *= (2.0**dlogs)
            apply(current_gid, tx,ty,theta,scale)
        elif code == 3:
            pass
        else:
            break
    return pts

def unpack_to_svg(blob: bytes, out_svg: str, width: int=800, height: int=300, font_family: str="sans-serif") -> str:
    import struct
    if not blob.startswith(MAGIC):
        raise ValueError("Not an ATCP2 blob")
    off = len(MAGIC)
    n, ext_len, txt_size, num_paths, num_layout = struct.unpack_from("<I H I H H", blob, off); off += struct.calcsize("<I H I H H")
    if ext_len > 0:
        ext_bytes = blob[off:off+ext_len]; off += ext_len
    text_bytes = blob[off:off+txt_size]; off += txt_size
    text = text_bytes.decode("utf-8")

    glyph_pts = []
    if blob[off:off+4] == GSEC:
        off += 4
        (ng,) = struct.unpack_from("<H", blob, off); off += 2
        for _ in range(ng):
            (idl,) = struct.unpack_from("<H", blob, off); off += 2
            gid = blob[off:off+idl]; off += idl
            (count,) = struct.unpack_from("<I", blob, off); off += 4
            if count == 0:
                glyph_pts.append([])
            else:
                x0, y0 = struct.unpack_from("<ii", blob, off); off += 8
                pts = [(x0,y0)]
                for _ in range(count-1):
                    dx, dy = struct.unpack_from("<hh", blob, off); off += 4
                    x0 += dx; y0 += dy
                    pts.append((x0,y0))
                glyph_pts.append(pts)

    paths_pts = []
    paths_eps = []
    for _ in range(num_paths):
        flags, eps, val = struct.unpack_from("<H f I", blob, off); off += struct.calcsize("<H f I")
        if flags == 2:
            ops_bytes = blob[off:off+val]; off += val
            pts = _reconstruct_from_glyph_ops(ops_bytes, glyph_pts)
            paths_pts.append(pts); paths_eps.append(eps)
        else:
            count = val
            if count == 0:
                paths_pts.append([]); paths_eps.append(eps); continue
            x0, y0 = struct.unpack_from("<ii", blob, off); off += 8
            pts = [(x0,y0)]
            for _ in range(count-1):
                dx, dy = struct.unpack_from("<hh", blob, off); off += 4
                x0 += dx; y0 += dy
                pts.append((x0,y0))
            paths_pts.append(pts); paths_eps.append(eps)

    layouts = []
    for _ in range(num_layout):
        idx, a, b, spacing, offset = struct.unpack_from("<H I I f f", blob, off); off += struct.calcsize("<H I I f f")
        layouts.append((idx, a, b, spacing, offset))

    def path_d(pts):
        if not pts: return ""
        d = [f"M {pts[0][0]},{pts[0][1]}"]
        for x,y in pts[1:]:
            d.append(f"L {x},{y}")
        return " ".join(d)

    svg_parts = []
    svg_parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
    svg_parts.append('<defs>')
    for i, pts in enumerate(paths_pts):
        d = path_d(pts)
        svg_parts.append(f'<path id="p{i}" d="{d}" fill="none" stroke="#ccc" stroke-width="1"/>')
    svg_parts.append('</defs>')
    for i, pts in enumerate(paths_pts):
        d = path_d(pts)
        svg_parts.append(f'<path d="{d}" fill="none" stroke="#e0e0e0" stroke-width="1"/>')
    for (idx,a,b,spacing,offset) in layouts:
        frag = (text[a:b]).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
        svg_parts.append(f'<text font-family="{font_family}" font-size="{spacing}px" letter-spacing="0.5px">')
        svg_parts.append(f'  <textPath href="#p{idx}" startOffset="{offset}">{frag}</textPath>')
    svg_parts.append('</svg>')
    Path(out_svg).write_text("\n".join(svg_parts), encoding="utf-8")
    return out_svg
