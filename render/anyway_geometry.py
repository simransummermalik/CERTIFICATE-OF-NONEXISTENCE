"""The house, built anyway: one level of No. 1 Holonomy Lane, built from every copy at once.

The proof says the cloister turns a frame of reference a quarter turn about the court stone,
and the stair lifts it 38'-8". Build the house regardless, room by room through every doorway,
and each of those copies must stand. One level is the union of the four copies turned about
the stone; the levels repeat every 38'-8" up the stair. (The hall's quarter inch is real too,
but at any drawable scale it vanishes into the thickness of a line.)

This script paints walls, floors, doors, windows and stair flights onto an exact grid (every
dimension is a whole number of eighth-inches), unions the four copies, and meshes the result
as solids. Run with the project venv; Blender reads the JSON it writes.

    .venv/bin/python render/anyway_geometry.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nonexistence.geometry import FOOT, rot2  # noqa: E402
from nonexistence.holonomy_lane import STOREY, build  # noqa: E402
from nonexistence.prove import layout  # noqa: E402

B = build()
POSE, _, _ = layout(B, avoid=B.seams)
CERT = json.loads((ROOT / "out/proof/certificate.json").read_text())

U = 96                                   # grid units per foot (eighth inches)
EXT = 0.75                               # wall thickness drawn beyond each room face, as on the plan
SLAB = 1.0
LAP = 4 * STOREY / FOOT                  # 38'-8"
_c5 = next(L for L in CERT["loops"] if L["seam"] == "C5")["world"]
PIVOT = ((int(_c5["pivot"][0]) + 2760) / FOOT, int(_c5["pivot"][1]) / FOOT)   # drawing -> plan frame
assert PIVOT == (18.75, 44.75), PIVOT
HOLES = 6


def F(u):
    return u / FOOT


def to_plan(key, lx, ly):
    m = POSE[key]
    x, y = rot2(m.r, lx, ly)
    return x + F(m.t[0]), y + F(m.t[1])


def turn(b, x, y):
    """Rotate a plan point b quarter-turns about the court stone."""
    px, py = PIVOT
    dx, dy = x - px, y - py
    for _ in range(b % 4):
        dx, dy = -dy, dx
    return px + dx, py + dy


class Copy:
    """One copy of the house, painted onto the shared grid, turned b quarter-turns."""

    def __init__(self, b, grid):
        self.b, self.g = b, grid
        ny, nx = len(grid.ys) - 1, len(grid.xs) - 1
        self.cls = np.zeros((ny, nx), np.int8)          # 0 void, 1 wall, 2 floor, 3 court, 4 solid
        self.lo = np.full((ny, nx), np.nan, np.float32)
        self.hi = np.full((ny, nx), np.nan, np.float32)
        self.holes = np.full((ny, nx, HOLES, 2), np.nan, np.float32)

    def region(self, key, pts):
        q = [turn(self.b, *to_plan(key, x, y)) if key else turn(self.b, x, y) for x, y in pts]
        return self.g.slices(q)

    def wall(self, key, pts, h):
        s = self.region(key, pts)
        self.cls[s] = 1
        self.lo[s] = -SLAB
        self.hi[s] = np.fmax(self.hi[s], h)

    def floor(self, key, pts):
        s = self.region(key, pts)
        self.cls[s] = 2
        self.holes[s] = np.nan

    def court(self, pts):
        s = self.region(None, pts)
        self.cls[s] = 3

    def void(self, key, pts):
        s = self.region(key, pts)
        self.cls[s] = 0
        self.holes[s] = np.nan

    def solid(self, key, pts, lo, hi):
        s = self.region(key, pts)
        self.cls[s] = 4
        self.lo[s] = lo
        self.hi[s] = hi
        self.holes[s] = np.nan

    def hole(self, key, pts, z0, z1):
        s = self.region(key, pts)
        h = self.holes[s]
        free = np.isnan(h[..., 0])
        first = np.argmax(free, axis=-1)
        has = free.any(axis=-1)
        sub = h.reshape(-1, HOLES, 2)
        idx = np.nonzero(has.ravel())[0]
        sub[idx, first.ravel()[idx], 0] = z0
        sub[idx, first.ravel()[idx], 1] = z1
        self.holes[s] = sub.reshape(h.shape)


class Grid:
    def __init__(self, xs, ys):
        self.xs = np.array(sorted(set(xs)), np.int64)
        self.ys = np.array(sorted(set(ys)), np.int64)

    def slices(self, pts):
        xs = [round(x * U) for x, _ in pts]
        ys = [round(y * U) for _, y in pts]
        i0, i1 = np.searchsorted(self.xs, min(xs)), np.searchsorted(self.xs, max(xs))
        j0, j1 = np.searchsorted(self.ys, min(ys)), np.searchsorted(self.ys, max(ys))
        return slice(j0, j1), slice(i0, i1)


# ----------------------------------------------------------------------------- what to paint
def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


STAIR = [k for k, r in B.rooms.items() if r.kind == "stair"]
ROOMS = [k for k, r in B.rooms.items() if r.kind != "stair" and k != "G5"]   # G5 stands where G1 does
SQ = (38.0, 26.0, 38.0 + 21.75, 26.0 + 21.75)                                   # the stair hall, inside
COURT = (7.0 + EXT, 33.0 + EXT, 30.5 - EXT, 56.5 - EXT)


def door_rect(key, dk, depth):
    r = B.rooms[key]
    d = r.doors[dk]
    fr = r.door_frame(dk)
    hw = F(d.width) / 2

    def loc(nx, ny):
        x, y = rot2(fr.r, nx, ny)
        return x + F(fr.t[0]), y + F(fr.t[1])
    return [loc(0, -hw), loc(depth, -hw), loc(depth, hw), loc(0, hw)], F(d.height)


def window_rect(key, wdw):
    r = B.rooms[key]
    hw, at = F(wdw.width) / 2, F(wdw.at)
    w, d = F(r.w), F(r.d)
    c, n, t = {"S": ((at, 0), (0, -1), (1, 0)), "N": ((at, d), (0, 1), (1, 0)),
               "W": ((0, at), (-1, 0), (0, 1)), "E": ((w, at), (1, 0), (0, 1))}[wdw.wall]
    return [(c[0] + n[0] * a + t[0] * s, c[1] + n[1] * a + t[1] * s) for a, s in
            ((0, -hw), (EXT, -hw), (EXT, hw), (0, hw))]


def paint(cp: Copy):
    for k in ROOMS:
        r = B.rooms[k]
        cp.wall(k, rect(-EXT, -EXT, F(r.w) + EXT, F(r.d) + EXT), F(r.h))
    cp.wall(None, rect(SQ[0] - EXT, SQ[1] - EXT, SQ[2] + EXT, SQ[3] + EXT), LAP - SLAB)
    for k in ROOMS:
        r = B.rooms[k]
        cp.floor(k, rect(0, 0, F(r.w), F(r.d)))
    cp.court(rect(*COURT))
    cp.void(None, rect(*SQ))
    # doorways between rooms, and the front door
    for g in B.gluings:
        if g.wall <= 0 or g.a == "G5":      # C5 leaves from G5, which stands in G1's place
            continue
        pts, h = door_rect(g.a, g.da, F(g.wall))
        cp.hole(g.a, pts, 0.0, h)
    pts, h = door_rect("ENT", "front", EXT)
    cp.hole("ENT", pts, 0.0, h)
    # the colonnade: five openings in each gallery's court-side wall
    for k in ("G1", "G2", "G3", "G4"):
        L = F(B.rooms[k].w)
        span = (L - 1.0 - 8.0) / 5
        for i in range(5):
            a = 8.0 + i * span + 0.9
            cp.hole(k, rect(a, -EXT, a + span - 1.8, 0), 0.0, 8.0)
    for k in ROOMS + STAIR:
        z = F(POSE[k].t[2])
        for wdw in B.rooms[k].windows:
            cp.hole(k, window_rect(k, wdw), z + F(wdw.sill), z + F(wdw.head))
    # the four flights: a landing, fifteen treads, and a parapet on the well side
    for k in STAIR:
        st, z = B.rooms[k].stair, F(POSE[k].t[2])
        x0, tr, rs, wd = F(st.x0), F(st.tread), F(st.riser), F(st.width)
        cp.solid(k, rect(0, 0, x0, wd), z - 0.75, z)
        for i in range(st.risers - 1):
            top = z + (i + 1) * rs
            cp.solid(k, rect(x0 + i * tr, 0, x0 + (i + 1) * tr, wd - 0.5), top - 0.75, top)
            cp.solid(k, rect(x0 + i * tr, wd - 0.5, x0 + (i + 1) * tr, wd), top - 0.75, top + 3.0)
    # the D08 door from the hall into the stair, through the stair hall's wall
    pts, h = door_rect("ST1", "D08", EXT)
    cp.hole("ST1", pts, 0.0, h)


def edges_of(b):
    """Every x and y the painter will use, in grid units, for copy b."""
    xs, ys = set(), set()

    class Probe:
        def slices(self, pts):
            for x, y in pts:
                xs.add(round(x * U))
                ys.add(round(y * U))
            return slice(0, 0), slice(0, 0)

    cp = Copy.__new__(Copy)
    cp.b, cp.g = b, Probe()
    cp.cls = np.zeros((0, 0), np.int8)
    cp.lo = cp.hi = np.zeros((0, 0), np.float32)
    cp.holes = np.zeros((0, 0, HOLES, 2), np.float32)
    paint(cp)
    return xs, ys


# ----------------------------------------------------------------------------- intervals
def intervals(cls, lo, hi, holes):
    if cls == 0:
        return ()
    if cls == 2:
        return ((-SLAB, 0.0),)
    if cls == 3:
        return ((-SLAB, -0.4),)
    if cls == 4:
        return ((float(lo), float(hi)),)
    segs = [(-SLAB, float(hi))]
    for z0, z1 in holes:
        if np.isnan(z0):
            continue
        out = []
        for a, b in segs:
            if z1 <= a or z0 >= b:
                out.append((a, b))
                continue
            if z0 > a:
                out.append((a, float(z0)))
            if z1 < b:
                out.append((float(z1), b))
        segs = out
    return tuple(segs)


def union(sets):
    segs = sorted(s for st in sets for s in st)
    out = []
    for a, b in segs:
        if out and a <= out[-1][1] + 1e-9:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return tuple(out)


def minus(A, Bs):
    """Parts of interval set A not covered by interval set Bs."""
    out = []
    for a, b in A:
        cur = [(a, b)]
        for c, d in Bs:
            nxt = []
            for p, q in cur:
                if d <= p or c >= q:
                    nxt.append((p, q))
                    continue
                if c > p:
                    nxt.append((p, c))
                if d < q:
                    nxt.append((d, q))
            cur = nxt
        out += cur
    return [(p, q) for p, q in out if q - p > 1e-6]


def build_level():
    xs, ys = set(), set()
    for b in range(4):
        ex, ey = edges_of(b)
        xs |= ex
        ys |= ey
    g = Grid(xs, ys)
    print(f"grid {len(g.xs)} x {len(g.ys)}")
    ids = []
    tables = []
    for b in range(4):
        cp = Copy(b, g)
        paint(cp)
        key = np.concatenate([cp.cls[..., None].astype(np.float32), cp.lo[..., None], cp.hi[..., None],
                              cp.holes.reshape(*cp.cls.shape, -1)], axis=-1)
        key = np.nan_to_num(key, nan=-999.0)
        flat = key.reshape(-1, key.shape[-1])
        uniq, inv = np.unique(flat, axis=0, return_inverse=True)
        table = []
        for row in uniq:
            hol = row[3:].reshape(HOLES, 2)
            hol = np.where(hol == -999.0, np.nan, hol)
            table.append(intervals(int(row[0]), row[1], row[2], hol))
        ids.append(inv.reshape(cp.cls.shape))
        tables.append(table)
    combo = np.stack(ids, axis=-1).reshape(-1, 4)
    uc, cinv = np.unique(combo, axis=0, return_inverse=True)
    sets = [union([tables[b][row[b]] for b in range(4)]) for row in uc]
    # renumber so identical interval sets share an id; id 0 is empty
    canon = {(): 0}
    remap = np.array([canon.setdefault(s, len(canon)) for s in sets], np.int32)
    G = remap[cinv].reshape(len(g.ys) - 1, len(g.xs) - 1)
    SETS = [None] * len(canon)
    for s, i in canon.items():
        SETS[i] = s
    return g, G, SETS


# ----------------------------------------------------------------------------- meshing
def mesh(g, G, SETS):
    X = g.xs / U
    Y = g.ys / U
    ny, nx = G.shape
    verts, faces, index = [], [], {}

    def vid(p):
        k = (round(float(p[0]) * U * 4), round(float(p[1]) * U * 4), round(float(p[2]) * 9600))
        if k not in index:
            index[k] = len(verts)
            verts.append(tuple(float(c) for c in p))
        return index[k]

    def quad(a, b, c, d):
        faces.append((vid(a), vid(b), vid(c), vid(d)))

    # tops and bottoms: merge runs of equal id along rows, then identical runs down the columns
    runs = {}
    for j in range(ny):
        row = G[j]
        cuts = np.nonzero(np.diff(row))[0] + 1
        starts = np.concatenate([[0], cuts])
        ends = np.concatenate([cuts, [nx]])
        for s, e in zip(starts, ends):
            v = int(row[s])
            if v:
                runs.setdefault((s, e, v), []).append(j)
    for (s, e, v), js in runs.items():
        js.sort()
        a = js[0]
        for k in range(1, len(js) + 1):
            if k == len(js) or js[k] != js[k - 1] + 1:
                b = js[k - 1] + 1
                x0, x1, y0, y1 = X[s], X[e], Y[a], Y[b]
                for z0, z1 in SETS[v]:
                    quad((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))
                    quad((x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0))
                if k < len(js):
                    a = js[k]

    # sides: where neighbouring cells differ, the uncovered part of each faces the other
    pad = np.zeros((ny + 2, nx + 2), np.int32)
    pad[1:-1, 1:-1] = G
    cache = {}

    def exposed(a, b):
        k = (a, b)
        if k not in cache:
            cache[k] = tuple(minus(SETS[a], SETS[b]))
        return cache[k]

    # vertical walls facing +x / -x, at x = X[i] between cell i-1 and i
    for i in range(nx + 1):
        L, R = pad[1:-1, i], pad[1:-1, i + 1]
        diff = L != R
        if not diff.any():
            continue
        x = X[i]
        for side in (0, 1):
            src, dst = (L, R) if side == 0 else (R, L)
            j = 0
            while j < ny:
                if not diff[j] or not src[j]:
                    j += 1
                    continue
                ex = exposed(int(src[j]), int(dst[j]))
                j1 = j + 1
                while j1 < ny and diff[j1] and src[j1] and exposed(int(src[j1]), int(dst[j1])) == ex:
                    j1 += 1
                y0, y1 = Y[j], Y[j1]
                for z0, z1 in ex:
                    if side == 0:      # solid on the left, face looks +x
                        quad((x, y0, z0), (x, y1, z0), (x, y1, z1), (x, y0, z1))
                    else:
                        quad((x, y1, z0), (x, y0, z0), (x, y0, z1), (x, y1, z1))
                j = j1
    for j in range(ny + 1):
        D, Uu = pad[j, 1:-1], pad[j + 1, 1:-1]
        diff = D != Uu
        if not diff.any():
            continue
        y = Y[j]
        for side in (0, 1):
            src, dst = (D, Uu) if side == 0 else (Uu, D)
            i = 0
            while i < nx:
                if not diff[i] or not src[i]:
                    i += 1
                    continue
                ex = exposed(int(src[i]), int(dst[i]))
                i1 = i + 1
                while i1 < nx and diff[i1] and src[i1] and exposed(int(src[i1]), int(dst[i1])) == ex:
                    i1 += 1
                x0, x1 = X[i], X[i1]
                for z0, z1 in ex:
                    if side == 0:      # solid below, face looks +y
                        quad((x1, y, z0), (x0, y, z0), (x0, y, z1), (x1, y, z1))
                    else:
                        quad((x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1))
                i = i1
    return verts, faces


CUT = 5.0          # the top level is cut open at this height, as a plan is


def cut(SETS, z=CUT):
    return [tuple((a, min(b, z)) for a, b in s if a < z) for s in SETS]


# ----------------------------------------------------------------------------- furniture
# Each room is furnished in its own frame (x along its width, y along its depth, feet from its
# south-west corner, z up from its floor), as an architect furnishes a plan. Every copy of the
# house carries the same furniture, so the beds of one copy stand in the bathrooms of another.
def box(x0, y0, x1, y1, z0, z1):
    return ("box", [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1)


def cyl(cx, cy, r, z0, z1, n=40):
    import math
    return ("box", [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n))
                    for i in range(n)], z0, z1)


def table(x0, y0, x1, y1, h=2.5):
    out = [box(x0, y0, x1, y1, h - 0.15, h)]
    for x, y in ((x0 + 0.25, y0 + 0.25), (x1 - 0.47, y0 + 0.25), (x0 + 0.25, y1 - 0.47), (x1 - 0.47, y1 - 0.47)):
        out.append(box(x, y, x + 0.22, y + 0.22, 0, h - 0.15))
    return out


def round_table(cx, cy, r, h=2.5):
    return [cyl(cx, cy, r, h - 0.12, h), cyl(cx, cy, 0.18, 0.1, h - 0.12, 16), cyl(cx, cy, r * 0.45, 0, 0.1, 24)]


SIDES = {"N": (0, 1), "S": (0, -1), "E": (1, 0), "W": (-1, 0)}


def chair(cx, cy, face, s=1.5):
    """A chair whose sitter looks toward `face`; its back is on the other side."""
    h = s / 2
    out = [box(cx - h, cy - h, cx + h, cy + h, 1.45, 1.6)]
    for x, y in ((cx - h + 0.06, cy - h + 0.06), (cx + h - 0.18, cy - h + 0.06),
                 (cx - h + 0.06, cy + h - 0.18), (cx + h - 0.18, cy + h - 0.18)):
        out.append(box(x, y, x + 0.12, y + 0.12, 0, 1.45))
    dx, dy = SIDES[face]
    if dx:
        x = cx - dx * h
        out.append(box(min(x, x + dx * 0.16), cy - h, max(x, x + dx * 0.16), cy + h, 1.6, 3.0))
    else:
        y = cy - dy * h
        out.append(box(cx - h, min(y, y + dy * 0.16), cx + h, max(y, y + dy * 0.16), 1.6, 3.0))
    return out


def _sides(x0, y0, x1, y1, side, t):
    """The strip of thickness t along one side of a rectangle."""
    return {"N": (x0, y1 - t, x1, y1), "S": (x0, y0, x1, y0 + t),
            "E": (x1 - t, y0, x1, y1), "W": (x0, y0, x0 + t, y1)}[side]


def _split(x0, y0, x1, y1, along_x, n, gap):
    out = []
    if along_x:
        w = (x1 - x0 - gap * (n - 1)) / n
        for i in range(n):
            a = x0 + i * (w + gap)
            out.append((a, y0, a + w, y1))
    else:
        w = (y1 - y0 - gap * (n - 1)) / n
        for i in range(n):
            a = y0 + i * (w + gap)
            out.append((x0, a, x1, a + w))
    return out


OPP = {"N": "S", "S": "N", "E": "W", "W": "E"}


def bed(x0, y0, x1, y1, head):
    out = [box(x0, y0, x1, y1, 0, 0.9), box(x0 + 0.08, y0 + 0.08, x1 - 0.08, y1 - 0.08, 0.9, 1.75)]
    out.append(box(*_sides(x0, y0, x1, y1, head, 0.3), 0, 3.4))
    along_x = head in "NS"
    hx0, hy0, hx1, hy1 = _sides(x0 + 0.35, y0 + 0.35, x1 - 0.35, y1 - 0.35, head, 1.3)
    wide = (x1 - x0) if along_x else (y1 - y0)
    for p in _split(hx0, hy0, hx1, hy1, along_x, 2 if wide > 4 else 1, 0.25):
        out.append(box(*p, 1.75, 2.15))
    out.append(box(*_sides(x0 + 0.04, y0 + 0.04, x1 - 0.04, y1 - 0.04, OPP[head], 2.1), 1.75, 1.92))
    return out


def sofa(x0, y0, x1, y1, back, seats=3):
    out = [box(x0, y0, x1, y1, 0.25, 1.3)]
    out.append(box(*_sides(x0, y0, x1, y1, back, 0.75), 1.3, 2.7))
    along_x = back in "NS"
    ends = ("W", "E") if along_x else ("S", "N")
    for e in ends:
        out.append(box(*_sides(x0, y0, x1, y1, e, 0.6), 1.3, 2.1))
    sx0, sy0, sx1, sy1 = x0, y0, x1, y1
    if along_x:
        sx0, sx1 = x0 + 0.6, x1 - 0.6
        sy0, sy1 = (y0, y1 - 0.75) if back == "N" else (y0 + 0.75, y1)
    else:
        sy0, sy1 = y0 + 0.6, y1 - 0.6
        sx0, sx1 = (x0, x1 - 0.75) if back == "E" else (x0 + 0.75, x1)
    for p in _split(sx0, sy0, sx1, sy1, along_x, seats, 0.08):
        out.append(box(*p, 1.3, 1.65))
    for x, y in ((x0 + 0.1, y0 + 0.1), (x1 - 0.3, y0 + 0.1), (x0 + 0.1, y1 - 0.3), (x1 - 0.3, y1 - 0.3)):
        out.append(box(x, y, x + 0.2, y + 0.2, 0, 0.25))
    return out


def armchair(cx, cy, face):
    h = 1.45
    return sofa(cx - h, cy - h, cx + h, cy + h, OPP[face], seats=1)


def piano(x, y):
    """A grand piano, keyboard to the north, its tail curving away to the south."""
    outline = [(0, 0), (4.9, 0), (4.9, 1.5), (4.8, 2.2), (4.5, 2.8), (4.0, 3.3), (3.4, 3.8), (2.9, 4.3),
               (2.5, 4.9), (2.3, 5.5), (2.0, 6.05), (1.5, 6.35), (0.8, 6.45), (0.2, 6.35), (0, 6.1)]
    pts = [(x + px, y - py) for px, py in outline][::-1]
    out = [("box", pts, 2.0, 3.05)]
    out.append(box(x + 0.15, y, x + 4.75, y + 0.95, 2.1, 2.45))                 # the keys
    for px, py in ((0.45, 0.45), (4.4, 0.5), (1.0, 5.7)):
        out.append(cyl(x + px, y - py, 0.17, 0, 2.0, 16))
    out.append(box(x + 1.2, y + 1.35, x + 3.7, y + 2.35, 0, 1.6))               # the bench
    return out


def lamp(cx, cy, z):
    return [cyl(cx, cy, 0.12, z, z + 0.9, 12), cyl(cx, cy, 0.42, z + 0.9, z + 1.6, 28)]


def tub(x0, y0, x1, y1, t=0.35):
    out = [box(x0, y0, x1, y1, 0, 0.5)]
    for s in "NSEW":
        out.append(box(*_sides(x0, y0, x1, y1, s, t), 0.5, 1.8))
    return out


FURNITURE = {
    "LIB": [box(6.0, 24.4, 17.6, 25.5, 0, 7.5), box(0, 11.6, 1.1, 14.4, 0, 7.5), box(0, 21.6, 1.1, 25.5, 0, 7.5),
            box(0, 0, 1.1, 4.4, 0, 7.5), box(1.1, 0, 4.4, 1.1, 0, 7.5), box(13.6, 0, 18.0, 1.1, 0, 7.5),
            box(16.9, 1.1, 18.0, 8.0, 0, 7.5), box(16.9, 12.5, 18.0, 20.5, 0, 7.5),
            *table(6.0, 13.0, 12.0, 16.5), *chair(7.5, 12.0, "N"), *chair(10.5, 12.0, "N"), *chair(9.0, 17.5, "S"),
            *armchair(3.2, 8.0, "E"), *lamp(2.0, 10.2, 0), box(4.5, 3.5, 13.5, 10.5, 0, 0.1)],
    "DIN": [*table(3.0, 13.0, 13.0, 16.5)] + [p for x in (4.5, 7.0, 9.5, 12.0) for p in chair(x, 12.0, "N") + chair(x, 17.5, "S")]
           + [box(3.5, 0, 12.5, 1.6, 0, 2.9)],
    "LIV": [box(6.0, 11.2, 16.0, 19.0, 0, 0.1), *sofa(7.0, 16.5, 16.0, 19.6, "N"), *table(9.5, 12.6, 13.5, 14.6, 1.3),
            *armchair(4.3, 14.2, "E"), *armchair(18.2, 14.2, "W"), *piano(2.4, 7.0), *lamp(19.8, 18.6, 0)],
    "ENT": [box(8.6, 2.0, 9.8, 7.5, 0, 1.5), *round_table(5.0, 18.5, 1.6, 2.6), cyl(5.0, 18.5, 0.32, 2.6, 3.7, 24)],
    "KIT": [box(0.2, 0, 15.8, 2.1, 0, 3.0), box(3.0, 23.4, 16.0, 25.5, 0, 3.0), box(0, 22.9, 3.0, 25.5, 0, 6.8),
            box(0, 2.1, 2.1, 9.5, 0, 3.0), box(5.5, 10.5, 11.5, 14.0, 0, 3.0),
            *[cyl(x, 15.0, 0.55, 0, 2.5, 24) for x in (6.5, 8.5, 10.5)]],
    "COR": [*table(30.5, 0.05, 34.5, 1.4, 2.6)],
    "BR1": [*bed(4.5, 7.2, 10.0, 14.0, "N"), box(2.9, 12.6, 4.3, 14.0, 0, 2.0), box(10.2, 12.6, 11.6, 14.0, 0, 2.0),
            *lamp(3.6, 13.3, 2.0), *lamp(10.9, 13.3, 2.0), box(0.1, 0, 4.8, 2.1, 0, 7.0),
            box(5.0, 5.6, 9.5, 6.8, 0, 1.5), box(3.5, 3.2, 11.0, 7.1, 0, 0.1)],
    "BR2": [*bed(1.6, 7.4, 5.0, 14.0, "N"), *bed(10.0, 7.4, 13.4, 14.0, "N"), box(6.6, 12.6, 8.4, 14.0, 0, 2.0),
            *lamp(7.5, 13.3, 2.0), *table(13.0, 1.5, 15.0, 6.0), *chair(12.3, 3.75, "E"), box(9.5, 0, 12.4, 1.8, 0, 3.2)],
    "BTH": [*tub(3.2, 12.6, 9.9, 15.15), box(3.0, 0, 7.0, 1.9, 0, 2.8), box(7.9, 0, 9.6, 0.75, 0, 2.6),
            cyl(8.75, 1.75, 0.65, 0, 1.35, 28)],
    "G1": [box(12.5, 5.4, 18.5, 6.6, 0, 1.5)], "G2": [box(12.5, 5.4, 18.5, 6.6, 0, 1.5)],
    "G3": [box(12.5, 5.4, 18.5, 6.6, 0, 1.5)], "G4": [box(12.5, 5.4, 18.5, 6.6, 0, 1.5)],
}
# the dark ceramic sphere on the hall table, as in the photograph
SPHERES = {"COR": [(32.5, 0.72, 2.6 + 0.55, 0.55)]}


def furniture(top=None):
    """Furniture of all four copies, as a mesh; with top, cut off there as the plan cuts the walls."""
    verts, faces = [], []
    for b in range(4):
        for key, items in FURNITURE.items():
            z = F(POSE[key].t[2])
            for _, pts, z0, z1 in items:
                if top is not None:
                    if z0 >= top:
                        continue
                    z1 = min(z1, top)
                q = [turn(b, *to_plan(key, x, y)) for x, y in pts]
                # wind counter-clockwise seen from above, so the faces look outward
                area = sum(q[i][0] * q[i - 1][1] - q[i - 1][0] * q[i][1] for i in range(len(q)))
                if area > 0:
                    q = q[::-1]
                n, i0 = len(q), len(verts)
                verts += [(x, y, z + z0) for x, y in q] + [(x, y, z + z1) for x, y in q]
                faces.append(list(range(i0 + n - 1, i0 - 1, -1)))
                faces.append(list(range(i0 + n, i0 + 2 * n)))
                for i in range(n):
                    j = (i + 1) % n
                    faces.append([i0 + i, i0 + j, i0 + n + j, i0 + n + i])
    spheres = [[*turn(b, *to_plan(k, x, y)), F(POSE[k].t[2]) + z, r]
               for b in range(4) for k, items in SPHERES.items() for x, y, z, r in items]
    return verts, faces, spheres


def main():
    g, G, SETS = build_level()
    out = ROOT / "out" / "anyway"
    out.mkdir(parents=True, exist_ok=True)
    for name, sets in (("level", SETS), ("level_cut", cut(SETS))):
        verts, faces = mesh(g, G, sets)
        data = {"lap": LAP, "pivot": PIVOT, "slab": SLAB, "cut": CUT,
                "verts": [[round(c, 5) for c in v] for v in verts], "faces": faces}
        (out / f"{name}.json").write_text(json.dumps(data, separators=(",", ":")))
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        print(f"{name}: {len(faces)} faces; x {min(xs):.1f}..{max(xs):.1f}, y {min(ys):.1f}..{max(ys):.1f}")
    for name, top in (("furniture", None), ("furniture_cut", CUT)):
        verts, faces, spheres = furniture(top)
        data = {"verts": [[round(c, 5) for c in v] for v in verts], "faces": faces, "spheres": spheres}
        (out / f"{name}.json").write_text(json.dumps(data, separators=(",", ":")))
        print(f"{name}: {len(faces)} faces, {len(spheres)} spheres")


if __name__ == "__main__":
    main()
