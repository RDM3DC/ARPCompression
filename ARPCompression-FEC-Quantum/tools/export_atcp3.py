#!/usr/bin/env python3
import argparse, base64, struct, math, sys
from pathlib import Path
import numpy as np

MAGIC = b"ATCP3\x01"

def rdp(points, eps):
    if len(points) < 3:
        return points[:]
    def perp_dist(p, a, b):
        (x,y),(x1,y1),(x2,y2)=p,a,b
        dx,dy=x2-x1,y2-y1
        if dx==0 and dy==0:
            return math.hypot(x-x1,y-y1)
        t=((x-x1)*dx+(y-y1)*dy)/(dx*dx+dy*dy)
        t=max(0.0,min(1.0,t))
        px=x1+t*dx; py=y1+t*dy
        return math.hypot(x-px,y-py)
    a,b=points[0],points[-1]
    maxd,idx=-1.0,-1
    for i in range(1,len(points)-1):
        d=perp_dist(points[i],a,b)
        if d>maxd: maxd,idx=d,i
    if maxd>eps:
        left=rdp(points[:idx+1],eps)
        right=rdp(points[idx:],eps)
        return left[:-1]+right
    else:
        return [a,b]

def normalize_trace_to_viewport(x, y, width, height, pad=30):
    x,y=np.asarray(x,float),np.asarray(y,float)
    xmin,xmax=float(np.min(x)),float(np.max(x))
    ymin,ymax=float(np.min(y)),float(np.max(y))
    xr=(x-xmin)/(xmax-xmin+1e-12)
    yr=(y-ymin)/(ymax-ymin+1e-12)
    X=pad + xr*(width-2*pad)
    Y=(height-pad) - yr*(height-2*pad)
    return list(zip(X.tolist(), Y.tolist()))

def sine_path(width,height,amp=0.25,periods=1.5,pad=30,samples=400):
    xs=np.linspace(pad,width-pad,samples)
    A=amp*(height-2*pad)
    k=2*math.pi*periods/(width-2*pad+1e-9)
    ys=(height/2.0)+A*np.sin(k*(xs-pad))
    return list(zip(xs.tolist(), ys.tolist()))

def quantize_linear_6bit(x):
    x=np.asarray(x,dtype=np.float32)
    xmin,xmax=float(x.min()),float(x.max())
    if xmax==xmin:
        return (np.zeros_like(x,dtype=np.uint8), xmin, xmax)
    q=np.round((x-xmin)*63.0/(xmax-xmin)).astype(np.uint8)
    q=np.clip(q,0,63)
    return q,xmin,xmax

def pack_binary_v3(container, blobs):
    text_ac=container["text_ac"]
    n=int(text_ac["n"])
    ext=text_ac.get("ext","").encode("utf-8")
    atc_data=base64.b64decode(text_ac["data_b64"])
    paths=container.get("paths",[]); layout=container.get("layout",[])
    out=bytearray(); out+=MAGIC
    import struct as st
    out+=st.pack("<I H I H H H", n, len(ext), len(atc_data), len(paths), len(layout), len(blobs))
    out+=ext; out+=atc_data
    for p in paths:
        anchors=p.get("anchors",[]); eps=float(p.get("max_err",0.0))
        out+=st.pack("<H f I", 0, eps, len(anchors))
        if anchors:
            x0,y0=int(round(anchors[0][0])),int(round(anchors[0][1]))
            out+=st.pack("<ii",x0,y0); px,py=x0,y0
            for (x,y) in anchors[1:]:
                dx=int(round(x))-px; dy=int(round(y))-py
                dx=max(-32768,min(32767,dx)); dy=max(-32768,min(32767,dy))
                out+=st.pack("<hh",dx,dy); px+=dx; py+=dy
    id2idx={p.get("id",f"p{i}"):i for i,p in enumerate(paths)}
    for lay in layout:
        idx=id2idx.get(lay.get("path","p0"),0)
        a,b=map(int, lay["range"]); spacing=float(lay.get("spacing_px",16)); offset=float(lay.get("offset_px",0))
        out+=st.pack("<H I I f f", idx, a, b, spacing, offset)
    for blob in blobs:
        bid=blob["id"].encode("utf-8"); shape=tuple(blob["shape"]); bits=int(blob["bits"])
        xmin=float(blob["xmin"]); xmax=float(blob["xmax"]); data=blob["data"]
        out+=st.pack("<H",len(bid))+bid
        out+=st.pack("<B",len(shape))
        for d in shape: out+=st.pack("<I",int(d))
        out+=st.pack("<BffI", bits, xmin, xmax, len(data))
        out+=data
    return bytes(out)

def render_svg_preview(container, width=800, height=500, font_family="sans-serif"):
    text=base64.b64decode(container["text_ac"]["data_b64"]).decode("utf-8",errors="ignore")
    paths=container.get("paths",[]); layout=container.get("layout",[])
    def path_d(pts):
        if not pts: return ""
        d=[f"M {int(round(pts[0][0]))},{int(round(pts[0][1]))}"]
        for x,y in pts[1:]:
            d.append(f"L {int(round(x))},{int(round(y))}")
        return " ".join(d)
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">','<defs>']
    for i,p in enumerate(paths):
        svg.append(f'<path id="p{i}" d="{path_d(p.get("anchors",[]))}" fill="none" stroke="#ccc" stroke-width="1"/>')
    svg.append('</defs>')
    for i,p in enumerate(paths):
        svg.append(f'<path d="{path_d(p.get("anchors",[]))}" fill="none" stroke="#e0e0e0" stroke-width="1"/>')
    for lay in layout:
        ids=[p.get("id",f"p{i}") for i,p in enumerate(paths)]
        idx=ids.index(lay.get("path","p0")) if lay.get("path","p0") in ids else 0
        a,b=lay["range"]; spacing=float(lay.get("spacing_px",16)); offset=float(lay.get("offset_px",0))
        frag=(text[a:b]).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
        svg.append(f'<text font-family="{font_family}" font-size="{spacing}px" letter-spacing="0.5px">')
        svg.append(f'  <textPath href="#p{idx}" startOffset="{offset}">{frag}</textPath>')
        svg.append('</text>')
    svg.append('</svg>')
    return "\n".join(svg)

def main():
    import argparse, numpy as np
    ap=argparse.ArgumentParser()
    ap.add_argument("--mode",choices=["trace","heatmap"],required=True)
    ap.add_argument("--csv",required=True)
    ap.add_argument("--xcol",type=int,default=0)
    ap.add_argument("--ycol",type=int,default=1)
    ap.add_argument("--text",type=str,default=None)
    ap.add_argument("--textfile",type=str,default=None)
    ap.add_argument("--out",required=True)
    ap.add_argument("--svg",type=str,default=None)
    ap.add_argument("--width",type=int,default=800)
    ap.add_argument("--height",type=int,default=500)
    ap.add_argument("--pad",type=int,default=30)
    ap.add_argument("--rdp",type=float,default=0.0)
    ap.add_argument("--bits",type=int,default=6)
    args=ap.parse_args()

    csv_path=Path(args.csv)
    text=args.text or ""
    if args.textfile:
        text=Path(args.textfile).read_text(encoding="utf-8")
    if not text:
        text=csv_path.stem.replace("_"," ")

    if args.mode=="trace":
        data=np.genfromtxt(str(csv_path),delimiter=",",dtype=float)
        if data.ndim==1: data=data.reshape(-1,2)
        x=data[:,args.xcol]; y=data[:,args.ycol]
        anchors=normalize_trace_to_viewport(x,y,args.width,args.height,pad=args.pad)
        if args.rdp>0: anchors=rdp(anchors,args.rdp)
        blobs=[]
    else:
        grid=np.genfromtxt(str(csv_path),delimiter=",",dtype=float)
        if grid.ndim==1:
            n=int(math.sqrt(grid.size)); grid=grid.reshape(n,n)
        q,xmin,xmax=quantize_linear_6bit(grid)
        blobs=[{"id":"blob0","shape":grid.shape,"bits":args.bits,"xmin":xmin,"xmax":xmax,"data":q.tobytes(order="C")}]
        anchors=sine_path(args.width,args.height,amp=0.25,periods=1.5,pad=args.pad,samples=400)

    text_b64=base64.b64encode(text.encode("utf-8")).decode("ascii")
    container={"format":"ATC-PATH-v1","units":"px",
        "text_ac":{"format":"ATC-AC2-v2","n":len(text),"ext":"","data_b64":text_b64},
        "paths":[{"id":"p0","anchors":anchors,"max_err":float(args.rdp)}],
        "layout":[{"path":"p0","range":[0,len(text)],"spacing_px":16,"offset_px":0}],
        "metadata":{"source_csv":csv_path.name,"mode":args.mode}
    }
    blob_bytes=pack_binary_v3(container,blobs)
    Path(args.out).write_bytes(blob_bytes)
    print(f"[OK] wrote ATCP3: {args.out} ({len(blob_bytes)} bytes)")
    if args.svg:
        svg=render_svg_preview(container,width=args.width,height=args.height)
        Path(args.svg).write_text(svg,encoding="utf-8")
        print(f"[OK] wrote SVG: {args.svg}")

if __name__=="__main__":
    main()
