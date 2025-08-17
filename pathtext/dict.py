
from typing import List, Tuple, Dict
import hashlib, math

Point = Tuple[float, float]

def _poly_arclen(pts: List[Point]) -> float:
    if len(pts) < 2: return 0.0
    s = 0.0
    for i in range(1, len(pts)):
        dx = pts[i][0]-pts[i-1][0]
        dy = pts[i][1]-pts[i-1][1]
        s += (dx*dx+dy*dy)**0.5
    return s

def _centroid(pts: List[Point]) -> Point:
    n = max(1, len(pts))
    sx = sum(p[0] for p in pts)
    sy = sum(p[1] for p in pts)
    return (sx/n, sy/n)

def _pca_angle(pts: List[Point]) -> float:
    cx, cy = _centroid(pts)
    sxx = syy = sxy = 0.0
    for x,y in pts:
        dx, dy = x-cx, y-cy
        sxx += dx*dx; syy += dy*dy; sxy += dx*dy
    angle = 0.5*math.atan2(2*sxy, (sxx - syy) + 1e-12)
    return angle

def fingerprint_exact(packed_bytes: bytes) -> int:
    h = hashlib.blake2b(packed_bytes, digest_size=8).digest()
    return int.from_bytes(h, 'little')

def fingerprint_geom(anchors: List[Point], M: int = 32) -> int:
    if not anchors: return 0
    L = _poly_arclen(anchors)
    if L <= 0: L = 1.0
    cx, cy = _centroid(anchors)
    ang = _pca_angle(anchors)
    ca, sa = math.cos(-ang), math.sin(-ang)

    norm = []
    for x,y in anchors:
        x2 = x - cx; y2 = y - cy
        xr = ca*x2 - sa*y2
        yr = sa*x2 + ca*y2
        norm.append((xr/L, yr/L))

    s = [0.0]
    for i in range(1, len(norm)):
        dx = norm[i][0]-norm[i-1][0]
        dy = norm[i][1]-norm[i-1][1]
        s.append(s[-1] + (dx*dx+dy*dy)**0.5)
    if s[-1] <= 0:
        samp = norm[:1]*M
    else:
        samp = []
        for k in range(M):
            t = k*s[-1]/(M-1 if M>1 else 1)
            i = 0
            while i+1 < len(s) and s[i+1] < t: i += 1
            if i+1 >= len(s):
                samp.append(norm[-1]); continue
            w = (t - s[i]) / max(1e-12, (s[i+1]-s[i]))
            xk = norm[i][0]*(1-w) + norm[i+1][0]*w
            yk = norm[i][1]*(1-w) + norm[i+1][1]*w
            samp.append((xk, yk))

    feats = []
    for i in range(1, M-1):
        x0,y0 = samp[i-1]
        x1,y1 = samp[i]
        x2,y2 = samp[i+1]
        ax, ay = x1-x0, y1-y0
        bx, by = x2-x1, y2-y1
        a = math.atan2(ay, ax)
        b = math.atan2(by, bx)
        dtheta = (b - a + math.pi)%(2*math.pi) - math.pi
        curv = abs(dtheta)
        qd = int(round(dtheta * 1024))
        qc = int(round(curv * 1024))
        feats.append((qd, qc))
    m = hashlib.blake2b(digest_size=8)
    for qd,qc in feats:
        m.update(qd.to_bytes(4, 'little', signed=True))
        m.update(qc.to_bytes(4, 'little', signed=True))
    return int.from_bytes(m.digest(), 'little')
