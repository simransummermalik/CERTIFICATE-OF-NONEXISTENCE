"""Ink the house, built anyway.

    .venv/bin/python drawings/anyway_ink.py out/anyway/test

Reads the exact passes written by render/anyway.py and draws them as a draughtsman would, in
one black ink:

  lines      where one surface passes in front of another (heavy) or folds (light), heavier
             near the eye and thinner as the tower falls away
  poché      walls and casework cut by the plan plane on the top storey, filled solid
  hatching   faces turned from the sun get an open hatch, cast shadows one twice as close
  gravel     the court is raked: rings round the stone, then squares out to the colonnade.
             Both patterns are unchanged by a quarter turn about the stone, as they must be,
             because all four houses share the court.
  stipple    the stone, the one round thing in the house
  the figure solid ink, with his footprints across the gravel

Everything fades with depth, because the tower does not end. Writes <prefix>_ink.png.
"""

import json
import math
import sys

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
HATCH = 9.0            # hatch spacing, output pixels
RAKE = 0.42            # gravel rake spacing, feet
COURT_HALF = 11.0      # the court is 22 ft square, centred on the stone
RINGS_TO = 7.0         # rings inside this half-width, squares outside
BUILDING, FURNITURE, STONE, FIGURE = 1, 2, 3, 4


def load16(path):
    im = Image.open(path)
    a = np.asarray(im)
    if im.mode.startswith("I;16") or a.dtype in (np.uint16, np.int32):
        return a.astype(np.float32) / 65535.0
    raise ValueError(f"{path} is not 16-bit greyscale ({im.mode})")


def shift(a, dy, dx):
    """a shifted so that out[y, x] = a[y + dy, x + dx], edges repeated."""
    h, w = a.shape[:2]
    yi = np.clip(np.arange(h) + dy, 0, h - 1)
    xi = np.clip(np.arange(w) + dx, 0, w - 1)
    return a[yi][:, xi]


def dilate(m, r):
    if r <= 0 or not m.any():
        return m.copy()
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if (dx or dy) and dx * dx + dy * dy <= r * r + 0.5:
                out |= shift(m, dy, dx)
    return out


def hash2(i, j, k=0.0):
    """A repeatable pseudo-random number in [0, 1) for each integer cell."""
    v = np.sin(i * 12.9898 + j * 78.233 + k * 37.719) * 43758.5453
    return v - np.floor(v)


def footprints(start, end, bend, pace=2.1):
    """Left and right footprints along a gently curved walk from start to end."""
    (x0, y0), (x1, y1) = start, end
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    cx, cy = mx - dy / L * bend, my + dx / L * bend

    def at(t):
        u = 1 - t
        return (u * u * x0 + 2 * u * t * cx + t * t * x1, u * u * y0 + 2 * u * t * cy + t * t * y1)
    steps = max(2, round(L / pace))
    prints = []
    for k in range(steps):                  # the last pace ends where he stands
        t = k / steps
        (ax, ay), (bx, by) = at(t), at(min(1, t + 0.01))
        hx, hy = bx - ax, by - ay
        h = math.hypot(hx, hy)
        hx, hy = hx / h, hy / h
        side = 1 if (steps - k) % 2 else -1
        prints.append((ax - hy * 0.3 * side, ay + hx * 0.3 * side, hx, hy))
    return prints


def ink(prefix, out=None, ss=None, far_fade=0.8):
    meta = json.load(open(f"{prefix}_meta.json"))
    scale = meta.get("ss", 1)          # how much larger than the sheet the passes are
    ss = scale if ss is None else ss   # how much to shrink the result here
    row0 = meta.get("row0", 0)

    def unit(name):                      # 0.02..1 back to 0..1; 0 means nothing was there
        return (load16(f"{prefix}_{name}.png") - 0.02) / 0.98

    D = load16(f"{prefix}_depth.png")
    alpha = D > 0.01
    H, W = alpha.shape
    n = np.stack([unit("nx"), unit("ny"), unit("nz")], axis=-1) * 2 - 1
    n /= np.linalg.norm(n, axis=-1, keepdims=True) + 1e-6
    lo, hi = meta["xy"]
    wx = lo + unit("wx") * (hi - lo)
    wy = lo + unit("wy") * (hi - lo)
    LAP = meta["lap"]
    wz = unit("wz") * LAP                                  # (z + 5) mod LAP
    plane = unit("plane") * 3000.0 - 1500.0
    ID = np.rint(load16(f"{prefix}_id.png") * 4).astype(np.int8)
    ID[~alpha] = 0
    dd = (D - 0.02) / 0.98
    d0, d1 = meta["depth"]
    if meta.get("inverse"):
        dist = 1.0 / np.maximum(1 / d1 + dd * (1 / d0 - 1 / d1), 1e-6)
    else:
        dist = d0 + dd * (d1 - d0)
    dist = np.where(alpha, dist, 1e9).astype(np.float32)
    px_ft = dist * meta.get("px_angle", 2.0 / meta.get("width", W))    # feet per pixel on the surface

    # ------------------------------------------------------------------ lines
    outline = np.zeros((H, W), bool)
    crease = np.zeros((H, W), bool)
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        ab = shift(alpha, dy, dx)
        nb = shift(n, dy, dx)
        db = shift(dist, dy, dx)
        ddx = wx - shift(wx, dy, dx)
        ddy = wy - shift(wy, dy, dx)
        ddz = wz - shift(wz, dy, dx)
        ddz -= LAP * np.round(ddz / LAP)
        both = alpha & ab
        sep = np.minimum(np.abs(n[..., 0] * ddx + n[..., 1] * ddy + n[..., 2] * ddz),
                         np.abs(nb[..., 0] * ddx + nb[..., 1] * ddy + nb[..., 2] * ddz))
        thr = np.maximum(0.06, 1.6 * px_ft * (1.42 if dx and dy else 1.0))
        step = both & (sep > thr)
        turn = both & ~step & ((n * nb).sum(-1) < 0.985)
        silhouette = alpha != ab
        near = dist <= db
        for mask, kind in ((step | silhouette, outline), (turn, crease)):
            kind |= mask & near
            kind |= shift(mask & ~near, -dy, -dx)       # the nearer pixel of the pair carries it
    outline &= alpha
    crease &= alpha

    if "depth_range" in meta:
        near_d, far_d = meta["depth_range"]
    else:
        near_d = np.percentile(dist[alpha], 1)
        far_d = np.percentile(dist[alpha], 99.5)
    k = np.clip(near_d / dist, 0, 1)
    furn = ID == FURNITURE
    big, mid = k > 0.72, (k > 0.4) & (k <= 0.72)
    r3 = outline & big & ~furn
    r2 = outline & ((big & furn) | (mid & ~furn))
    lines_o = dilate(r3, 3) | dilate(r2, 2) | dilate(outline & ~r3 & ~r2, 1)
    c2 = crease & big & ~furn
    lines_c = (dilate(c2, 2) | dilate(crease & ~c2, 1)) & ~lines_o

    t = np.clip((dist - near_d) / (far_d - near_d), 0, 1)
    fade = np.where(alpha, far_fade * t ** 0.75, far_fade)
    live = 1.0 - fade

    # ------------------------------------------------------------------ tone
    img = np.ones((H, W), np.float32)
    sx, sy = np.abs(n[..., 0]), np.abs(n[..., 1])
    tone = np.where(n[..., 2] > 0.9, 1.0, np.where(sx > sy, 0.955, 0.925))
    tone = np.where(furn, tone * 0.975, tone)
    img = np.where(alpha, 1 - (1 - tone) * live, img)

    # shade and shadow, hatched at forty-five degrees on the sheet
    lit = load16(f"{prefix}_light.png") / 0.9
    sun = np.array(meta["sun"], np.float32)
    ndl = (n * sun).sum(-1)
    hatchable = alpha & (ID <= FURNITURE)
    shade = hatchable & (ndl <= 0.02)
    shadow = hatchable & (ndl > 0.02) & (lit < 0.5 * ndl)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    yy += row0
    sp, wd = HATCH * scale, 0.75 * scale

    def stripes(u):
        d = np.abs((u % sp) - sp / 2)                    # distance to the nearest line, sheet pixels
        return np.clip(wd - (sp / 2 - d) + 0.5, 0, 1)    # 1 on the line, soft over a pixel
    u = (xx + yy) / math.sqrt(2)
    h1 = stripes(u)
    h2 = stripes(u + 0.5 * sp)                           # the lines between: twice as close
    hatch = np.where(shade, h1, 0.0)
    hatch = np.where(shadow, np.maximum(h1, h2), hatch)
    img *= 1 - 0.85 * hatch * live

    # the court, raked
    px, py = meta["pivot"]
    rx, ry = wx - px, wy - py
    court = alpha & (ID == BUILDING) & (n[..., 2] > 0.99) & (np.abs(wz - 4.6) < 0.05) & \
        (np.maximum(np.abs(rx), np.abs(ry)) < COURT_HALF)
    if court.any():
        cheb = np.maximum(np.abs(rx), np.abs(ry))
        r = np.where(cheb < RINGS_TO, np.hypot(rx, ry), cheb)
        # stop the rings a little short of the square they meet, as a rake turns
        phase = ((r - 2.9) / RAKE) % 1.0
        dft = np.abs(phase - 0.5) * RAKE                 # feet to the nearest groove
        g = np.hypot(*np.gradient(r)) + 1e-6             # feet per pixel across the grooves
        width = 0.65 * scale
        groove = np.clip(width - (RAKE / 2 - dft) / g + 0.5, 0, 1)
        groove = np.where(np.hypot(rx, ry) < 2.9, 0.0, groove)
        boundary = np.abs(cheb - RINGS_TO) / g < 0.6 * scale
        groove = np.where(boundary, 1.0, groove)
        # his footprints, from the colonnade to where he stands
        fx, fy = meta["figure"]
        foot = np.zeros((H, W), bool)
        for qx, qy, hx, hy in footprints((px - 4.0, py + 10.4), (fx, fy), bend=-1.0):
            ax, ay = wx - qx, wy - qy
            along, across = ax * hx + ay * hy, -ax * hy + ay * hx
            foot |= ((along - 0.16) / 0.3) ** 2 + (across / 0.17) ** 2 < 1     # sole
            foot |= ((along + 0.3) / 0.14) ** 2 + (across / 0.13) ** 2 < 1     # heel
        foot &= court
        groove = np.where(foot, 0.0, groove)
        img = np.where(court, img * (1 - 0.6 * groove * live), img)
        rim = dilate(foot, max(1, scale)) & ~foot & court
        img = np.where(foot, img * (1 - 0.5 * live), img)
        img = np.where(rim, img * (1 - 0.7 * live), img)

    # the stone, stippled: dots on a jittered grid, more of them where the sun does not reach
    stone = alpha & (ID == STONE)
    if stone.any():
        cell = 2.4 * scale
        dark = np.clip(1 - lit, 0, 1) ** 1.2
        density = np.where(stone, 0.06 + 0.88 * dark, 0.0)
        ys, xs = np.nonzero(stone)
        ci = np.arange(int(xs.min() // cell) - 1, int(xs.max() // cell) + 2)
        cj = np.arange(int((ys.min() + row0) // cell) - 1, int((ys.max() + row0) // cell) + 2)
        CI, CJ = np.meshgrid(ci, cj)
        X = (CI + hash2(CI, CJ, 1)) * cell
        Y = (CJ + hash2(CI, CJ, 2)) * cell - row0
        keep = (X >= 0) & (X < W) & (Y >= 0) & (Y < H)
        X, Y, tau = X[keep], Y[keep], hash2(CI, CJ, 3)[keep]
        on = tau < density[Y.astype(int), X.astype(int)]
        X, Y = X[on], Y[on]
        dots = np.zeros((H, W), np.float32)
        rad = 0.85 * scale
        R = int(math.ceil(rad + 1))
        for oy in range(-R, R + 1):
            for ox in range(-R, R + 1):
                yi = np.floor(Y).astype(int) + oy
                xi = np.floor(X).astype(int) + ox
                d = np.hypot(xi + 0.5 - X, yi + 0.5 - Y)
                v = np.clip(rad - d + 0.5, 0, 1)
                ok = (yi >= 0) & (yi < H) & (xi >= 0) & (xi < W)
                np.maximum.at(dots, (yi[ok], xi[ok]), v[ok])
        img = np.where(stone, img * (1 - 0.92 * dots * live), img)

    # lines over everything
    img = np.where(lines_c, img * (1 - 0.8 * live), img)
    img = np.where(lines_o, img * (1 - live), img)
    # the plan cut, and the figure
    cut = alpha & (ID <= FURNITURE) & (n[..., 2] > 0.99) & (np.abs(plane - meta["cut_z"]) < 0.05)
    img = np.where(cut, 0.06, img)
    img = np.where(alpha & (ID == FIGURE), 0.07, img)

    img8 = (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)
    im = Image.fromarray(img8, "L")
    if ss > 1:
        im = im.resize((im.width // ss, im.height // ss), Image.BOX)
    im.save(out or f"{prefix}_ink.png")
    return im


if __name__ == "__main__":
    ink(sys.argv[1])
    print("inked", sys.argv[1])
