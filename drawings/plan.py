"""Plate II — THE FLOOR PLAN.  Sheet A-101.

Every room is drawn in place by walking a spanning tree out from the front
door. Three doorways cannot be drawn in place; the inspector has marked them
in red.
"""

from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from drawings.svg import SVG, U, pt, mm, INK, RED, GREY, dim, cloud, arrowhead, tick  # noqa: E402
from nonexistence.geometry import FOOT, fmt_len, fmt_inches, rot2  # noqa: E402
from nonexistence.holonomy_lane import (build, STOREY, RISER, TREAD, LANDING, FLIGHT_L, FLIGHT_W,  # noqa: E402
                                        STAIR_S, GAL_S, GAL_L, GAL_W)
from nonexistence.prove import layout  # noqa: E402

CERT = json.loads((ROOT / "out/proof/certificate.json").read_text())
B = build()
POSE, PARENT, TREE = layout(B, avoid=B.seams)
WHITE = "#ffffff"
FAINT = "#9a968e"
SERIF = "Baskerville"
COND = "Avenir Next Condensed"
TITLE = "DIN Condensed"
ARTIST = (ROOT / "ARTIST.txt").read_text().strip() if (ROOT / "ARTIST.txt").exists() else "THE ARTIST"

svg = SVG(18, 24)

# ----------------------------------------------------------------------------- plan frame
SCALE = 12.5                    # units per foot  (1/8" = 1'-0")
OX, OY = 205.0, 1162.0          # sheet position of the plan's origin


def F(u):                       # quarter inches -> feet
    return u / FOOT


def P(x, y, s=SCALE, ox=None, oy=None):
    return ((OX if ox is None else ox) + x * s, (OY if oy is None else oy) - y * s)


def world(key, lx, ly):
    """Room-local feet -> drawing feet."""
    m = POSE[key]
    x, y = rot2(m.r, lx, ly)
    return x + F(m.t[0]), y + F(m.t[1])


def room_poly(key, e=(0, 0, 0, 0)):
    """Room rectangle in drawing feet, optionally grown by (W, S, E, N) in its own frame."""
    r = B.rooms[key]
    w, d = F(r.w), F(r.d)
    eW, eS, eE, eN = e
    pts = [(-eW, -eS), (w + eE, -eS), (w + eE, d + eN), (-eW, d + eN)]
    return [world(key, x, y) for x, y in pts]


def bbox(pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def S(pts, **kw):
    return [P(x, y, **kw) for x, y in pts]


EXT = 0.75   # poché thickness beyond each room face
DRAWN = [k for k in B.rooms if k != "G5"]


def grow(key):
    r = B.rooms[key]
    if r.kind == "stair":
        return (EXT, EXT, 0, 0)        # outer end wall and long wall only; the well is open
    return (EXT, EXT, EXT, EXT)


# ----------------------------------------------------------------------------- 1. walls
svg.open(id="walls")
for k in DRAWN:
    svg.poly(S(room_poly(k, grow(k))), w=0, fill=INK, closed=True)
svg.close()

# interiors
for k in DRAWN:
    svg.poly(S(room_poly(k)), w=0, fill=WHITE, closed=True)

# stair well and court are voids
sx0, sy0 = 38.0, 26.0
SS = F(STAIR_S)
well = [(sx0 + 4, sy0 + 4), (sx0 + SS - 4, sy0 + 4), (sx0 + SS - 4, sy0 + SS - 4), (sx0 + 4, sy0 + SS - 4)]
svg.poly(S(well), w=0, fill=WHITE, closed=True)
GS = F(GAL_S)
gcx, gcy = GS / 2, 26 + GS / 2
court = [(7 + EXT, 33 + EXT), (30.5 - EXT, 33 + EXT), (30.5 - EXT, 56.5 - EXT), (7 + EXT, 56.5 - EXT)]
# piers of the colonnade: open the court-side walls between piers
for k in ("G1", "G2", "G3", "G4"):
    r = B.rooms[k]
    L = F(r.w)
    n = 5
    for i in range(n):
        span = (L - 1.0 - 8.0) / n
        a = 8.0 + i * span + 0.9
        b_ = a + span - 1.8
        pts = [world(k, a, -EXT - 0.01), world(k, b_, -EXT - 0.01), world(k, b_, 0.01), world(k, a, 0.01)]
        svg.poly(S(pts), w=0, fill=WHITE, closed=True)
        # thin lines: the colonnade's sill and the line of the arch above
        svg.line(*P(*world(k, a, -EXT / 2)), *P(*world(k, b_, -EXT / 2)), w=mm(0.09), color=FAINT, dash="3,3")
svg.poly(S(court), w=mm(0.18), fill="none", closed=True, color=INK)


# ----------------------------------------------------------------------------- 2. doorways
def door_world(key, dk):
    r = B.rooms[key]
    d = r.doors[dk]
    fr = r.door_frame(dk)
    hw = F(d.width) / 2

    def loc(nx, ny):          # door-frame feet -> room-local feet
        x, y = rot2(fr.r, nx, ny)
        return x + F(fr.t[0]), y + F(fr.t[1])
    return d, hw, loc


def cut(key, dk, depth):
    d, hw, loc = door_world(key, dk)
    pts = [loc(-0.02, -hw), loc(depth, -hw), loc(depth, hw), loc(-0.02, hw)]
    svg.poly(S([world(key, *p) for p in pts]), w=0, fill=WHITE, closed=True)


for g in B.gluings:
    if g.a == "G5" or g.b == "G5":
        continue
    if g.wall > 0:
        cut(g.a, g.da, F(g.wall) + 0.02)
        # jamb lines
        d, hw, loc = door_world(g.a, g.da)
        for s_ in (-hw, hw):
            svg.line(*P(*world(g.a, *loc(0, s_))), *P(*world(g.a, *loc(F(g.wall), s_))), w=mm(0.18))
cut("ENT", "front", EXT + 0.02)


def door_leaf(key, dk, hinge=-1, color=INK):
    d, hw, loc = door_world(key, dk)
    w = 2 * hw
    h = hinge * hw
    p_h = world(key, *loc(0, h))
    p_t = world(key, *loc(-w, h))
    svg.line(*P(*p_h), *P(*p_t), w=mm(0.35), color=color)
    pts = []
    for i in range(25):
        a = math.pi / 2 * i / 24
        nx, ny = -w * math.cos(a), h - hinge * w * math.sin(a)
        pts.append(P(*world(key, *loc(nx, ny))))
    svg.poly(pts, w=mm(0.13), color=color)


for g in B.gluings:
    A = B.rooms[g.a]
    if A.doors[g.da].kind == "door" and "G5" not in (g.a, g.b):
        door_leaf(g.a, g.da, hinge=-1 if hash(g.key) % 2 else 1)
door_leaf("ENT", "front", hinge=1)


# ----------------------------------------------------------------------------- 3. windows
def window(key, wdw):
    r = B.rooms[key]
    hw = F(wdw.width) / 2
    at = F(wdw.at)
    w, d = F(r.w), F(r.d)
    # local frame: point on wall + outward normal
    if wdw.wall == "S":
        c, n, t = (at, 0), (0, -1), (1, 0)
    elif wdw.wall == "N":
        c, n, t = (at, d), (0, 1), (1, 0)
    elif wdw.wall == "W":
        c, n, t = (0, at), (-1, 0), (0, 1)
    else:
        c, n, t = (w, at), (1, 0), (0, 1)

    def L(a, s):
        return world(key, c[0] + n[0] * a + t[0] * s, c[1] + n[1] * a + t[1] * s)
    svg.poly(S([L(-0.02, -hw), L(EXT + 0.02, -hw), L(EXT + 0.02, hw), L(-0.02, hw)]), w=0, fill=WHITE, closed=True)
    for a in (0.0, EXT * 0.42, EXT * 0.58, EXT):
        svg.line(*P(*L(a, -hw)), *P(*L(a, hw)), w=mm(0.13) if 0 < a < EXT else mm(0.18))
    for s_ in (-hw, hw):
        svg.line(*P(*L(0, s_)), *P(*L(EXT, s_)), w=mm(0.18))


for k in DRAWN:
    for wdw in B.rooms[k].windows:
        if B.rooms[k].kind == "stair" and wdw.sill > 0 and wdw.at > LANDING:
            window(k, wdw)
        elif B.rooms[k].kind != "stair":
            window(k, wdw)
        else:
            window(k, wdw)


# ----------------------------------------------------------------------------- 4. floors
def clip_room(k):
    return svg.clip_poly(S(room_poly(k)))


def boards(k, spacing, along="x", w=mm(0.07), color="#b9b4aa", stagger=None):
    r = B.rooms[k]
    W, D = F(r.w), F(r.d)
    cp = clip_room(k)
    svg.open(clip_path=cp)
    if along == "x":
        y = spacing
        i = 0
        while y < D:
            svg.line(*P(*world(k, 0, y)), *P(*world(k, W, y)), w=w, color=color)
            if stagger:
                x = (i * 1.7) % stagger
                while x < W:
                    svg.line(*P(*world(k, x, y - spacing)), *P(*world(k, x, y)), w=w, color=color)
                    x += stagger
            y += spacing
            i += 1
    else:
        x = spacing
        i = 0
        while x < W:
            svg.line(*P(*world(k, x, 0)), *P(*world(k, x, D)), w=w, color=color)
            if stagger:
                y = (i * 2.3) % stagger
                while y < D:
                    svg.line(*P(*world(k, x - spacing, y)), *P(*world(k, x, y)), w=w, color=color)
                    y += stagger
            x += spacing
            i += 1
    svg.close()


def tiles(k, size, color="#c4bfb5", checker=False):
    r = B.rooms[k]
    W, D = F(r.w), F(r.d)
    cp = clip_room(k)
    svg.open(clip_path=cp)
    if checker:
        for i in range(int(W / size) + 1):
            for j in range(int(D / size) + 1):
                if (i + j) % 2 == 0:
                    pts = [world(k, i * size, j * size), world(k, (i + 1) * size, j * size),
                           world(k, (i + 1) * size, (j + 1) * size), world(k, i * size, (j + 1) * size)]
                    svg.poly(S(pts), w=0, fill="#e4e0d8", closed=True)
    x = size
    while x < W:
        svg.line(*P(*world(k, x, 0)), *P(*world(k, x, D)), w=mm(0.07), color=color)
        x += size
    y = size
    while y < D:
        svg.line(*P(*world(k, 0, y)), *P(*world(k, W, y)), w=mm(0.07), color=color)
        y += size
    svg.close()


boards("LIB", 0.42, "y", stagger=6.0)
boards("DIN", 0.42, "x", stagger=7.0)
boards("LIV", 0.42, "x", stagger=7.0)
boards("COR", 0.36, "x", stagger=9.0)
tiles("ENT", 2.0, checker=True)
tiles("KIT", 1.0)
tiles("BTH", 0.75)
boards("BR1", 0.42, "y", stagger=6.5)
boards("BR2", 0.42, "y", stagger=6.5)
for k in ("G1", "G2", "G3", "G4"):
    tiles(k, 1.75, color="#cbc6bc")


# ----------------------------------------------------------------------------- 5. the court
def court_rings():
    """Raked gravel. About the stone the angles add to 450°, so every circle is 5/4 too long
    to lie flat; drawn in the plane, each one ruffles."""
    cp = svg.clip_poly(S(court))
    svg.open(clip_path=cp)
    lam = 2.4
    r = 2.6
    while r < 16.5:
        n = max(5, round(2 * math.pi * r / lam))
        eps = 1.0 / n                      # length ≈ 2πr(1 + (nε)²/4) = 2πr · 5/4
        pts = []
        for i in range(721):
            t = 2 * math.pi * i / 720
            rr = r * (1 + eps * math.sin(n * t))
            pts.append(P(gcx + rr * math.cos(t), gcy + rr * math.sin(t)))
        svg.poly(pts, w=mm(0.09), color="#8f8a80")
        r += 0.95
    svg.close()
    # the stone
    random.seed(7)
    pts = []
    for i in range(14):
        t = 2 * math.pi * i / 14
        rr = 1.5 + random.uniform(-0.25, 0.25)
        pts.append(P(gcx + rr * math.cos(t) * 1.15, gcy + rr * math.sin(t) * 0.92))
    svg.poly(pts, w=mm(0.35), fill=WHITE, closed=True)
    for i in range(7):
        y = gcy - 1.1 + i * 0.36
        svg.line(*P(gcx - 1.2 + abs(i - 3) * 0.18, y), *P(gcx + 1.2 - abs(i - 3) * 0.2, y + 0.25), w=mm(0.07), color=GREY)


court_rings()


# ----------------------------------------------------------------------------- 6. stair
def stair():
    for k in range(4):
        key = f"ST{k+1}"
        L, Wf = F(LANDING), F(FLIGHT_W)
        for i in range(16):
            x = L + i * F(TREAD)
            svg.line(*P(*world(key, x, 0)), *P(*world(key, x, Wf - 0.5)), w=mm(0.13))
        # parapet
        for y in (Wf - 0.5, Wf):
            svg.line(*P(*world(key, L - 0.5 if y == Wf - 0.5 else L, y)), *P(*world(key, F(FLIGHT_L), y)), w=mm(0.25))
        svg.poly(S([world(key, L - 0.5, Wf - 0.5), world(key, L, Wf - 0.5), world(key, L, Wf), world(key, L - 0.5, Wf)]),
                 w=mm(0.25), fill=INK, closed=True)
    # The UP arrow: one continuous loop, arriving at its own beginning.
    pts = []
    for k in range(4):
        key = f"ST{k+1}"
        pts.append(world(key, 2.0, 1.75))
        pts.append(world(key, F(FLIGHT_L) + 2.0, 1.75))
    sp = S(pts)
    svg.poly(sp + [sp[0]], w=mm(0.25))
    for k in range(4):
        key = f"ST{k+1}"
        a = P(*world(key, 9.5, 1.75))
        b_ = P(*world(key, 10.5, 1.75))
        arrowhead(svg, *b_, math.atan2(b_[1] - a[1], b_[0] - a[0]), size=9)
    c0 = P(*world("ST1", 2.0, 1.75))
    svg.circle(*c0, 4.2, sw=mm(0.25), fill=WHITE)
    up = P(*world("ST1", 5.0, 2.55))
    svg.text(*up, "UP", size=pt(5), family=COND, weight=600, anchor="middle")
    # landing numerals
    for k in range(4):
        q = P(*world(f"ST{k+1}", 0.95, 3.0))
        svg.text(q[0], q[1] + 3, str(k + 1), size=pt(8), family=TITLE, weight=700, anchor="middle")


stair()


# ----------------------------------------------------------------------------- 7. furniture
FURN = "#55524c"


def frect(k, x0, y0, x1, y1, w=mm(0.13), fill="none", dash=None, color=FURN):
    svg.poly(S([world(k, x0, y0), world(k, x1, y0), world(k, x1, y1), world(k, x0, y1)]),
             w=w, fill=fill, closed=True, dash=dash, color=color)


def fcircle(k, x, y, r, w=mm(0.13)):
    svg.circle(*P(*world(k, x, y)), r * SCALE, stroke=FURN, sw=w, fill=WHITE)


def chairs_along(k, x0, x1, y, n, facing):
    for i in range(n):
        cx = x0 + (x1 - x0) * (i + 0.5) / n
        frect(k, cx - 0.8, y - (0 if facing > 0 else 1.5), cx + 0.8, y + (1.5 if facing > 0 else 0), fill=WHITE)


# Library: reading table under the west windows, stacks to the east, a chair.
frect("LIB", 2.0, 5.0, 6.0, 17.5, fill=WHITE)
for y in (6.2, 8.6, 11.0, 13.4, 15.8):
    frect("LIB", 0.9, y - 0.75, 2.0, y + 0.75, fill=WHITE)
    frect("LIB", 6.0, y - 0.75, 7.1, y + 0.75, fill=WHITE)
for x in (10.0, 12.6, 15.2):
    frect("LIB", x, 4.0, x + 1.3, 16.0, fill=WHITE)
    for j in range(24):
        yy = 4.0 + j * 0.5
        svg.line(*P(*world("LIB", x + 0.65, yy)), *P(*world("LIB", x + 0.65, yy + 0.5)), w=mm(0.05), color=FURN)
frect("LIB", 0.0, 22.0, 1.25, 25.5, fill=WHITE)
frect("LIB", 9.0, 19.5, 12.0, 22.5, fill=WHITE)
# Dining
frect("DIN", 3.0, 7.75, 13.0, 12.25, fill=WHITE)
chairs_along("DIN", 3.0, 13.0, 12.25, 5, 1)
chairs_along("DIN", 3.0, 13.0, 7.75, 5, -1)
# Living
frect("LIV", 4.0, 3.0, 18.0, 15.0, dash="4,3")
frect("LIV", 7.0, 12.0, 15.0, 15.0, fill=WHITE)
frect("LIV", 8.5, 7.0, 13.5, 9.5, fill=WHITE)
fcircle("LIV", 5.3, 7.5, 1.4)
fcircle("LIV", 16.7, 7.5, 1.4)
# Entrance hall: round table
fcircle("ENT", 5.0, 13.0, 2.2)
# Kitchen
frect("KIT", 14.0, 1.5, 16.0, 24.0, fill=WHITE)
frect("KIT", 0.5, 0.0, 14.0, 2.0, fill=WHITE)
frect("KIT", 5.0, 9.0, 8.5, 17.0, fill=WHITE)
for (x, y) in ((14.6, 15.0), (15.4, 15.0), (14.6, 16.0), (15.4, 16.0)):
    fcircle("KIT", x, y, 0.33)
frect("KIT", 7.0, 0.3, 9.0, 1.6)
# Bedrooms
for k, cx in (("BR1", 7.25), ("BR2", 7.5)):
    frect(k, cx - 2.6, 6.0, cx + 2.6, 14.0, fill=WHITE)
    frect(k, cx - 2.3, 12.5, cx + 2.3, 13.7, fill=WHITE)
    frect(k, cx - 4.4, 12.4, cx - 2.9, 13.9, fill=WHITE)
    frect(k, cx + 2.9, 12.4, cx + 4.4, 13.9, fill=WHITE)
# Bath
frect("BTH", 0.0, 0.0, 2.5, 5.5, fill=WHITE)
svg.poly(S([world("BTH", 0.3, 0.3), world("BTH", 2.2, 0.3), world("BTH", 2.2, 5.2), world("BTH", 0.3, 5.2)]),
         w=mm(0.09), color=FURN, closed=True, join="round")
frect("BTH", 7.5, 6.0, 10.0, 11.0, fill=WHITE)
fcircle("BTH", 8.6, 13.4, 0.9)


# ----------------------------------------------------------------------------- 8. tags
def area_sf(k):
    r = B.rooms[k]
    return r.w * r.d / FOOT / FOOT


def room_tag(k, x, y, rotate=None, size=6.2, show_area=True, color=INK):
    r = B.rooms[k]
    p = P(x, y)
    svg.text(p[0], p[1], (r.label or r.name).upper(), size=pt(size), family=COND, weight=600, anchor="middle",
             spacing=1.2, rotate=rotate, color=color)
    if show_area:
        q = (p[0], p[1] + pt(size) * 1.05) if not rotate else (p[0] + pt(size) * 1.05, p[1])
        svg.text(*q, f"{area_sf(k):,.0f} SF", size=pt(size * 0.72), family=COND, weight=500,
                 anchor="middle", rotate=rotate, color=color)


room_tag("LIB", 9.0, 22.6, size=6.4)
room_tag("DIN", 26.5, 3.4)
room_tag("LIV", 46.0, 2.6)
room_tag("ENT", 62.5, 5.0, size=5.6)
room_tag("KIT", 72.0, 6.0)
room_tag("BR1", 7.25, 70.4)
room_tag("BR2", 22.5, 70.4)
room_tag("BTH", 41.8, 59.5, size=5.6)
c = P(36.5, 23.7)
svg.text(*c, "THE HALL", size=pt(6.2), family=COND, weight=600, anchor="middle", spacing=1.2)
svg.text(c[0], c[1] + pt(6.2) * 1.05, f"{area_sf('COR'):,.2f} SF", size=pt(4.6), family=COND, anchor="middle")
for k, (x, y, rot) in {"G1": (19.5, 29.6, None), "G2": (3.6, 41.0, -90), "G3": (16.0, 60.2, None),
                      "G4": (34.0, 47.0, 90)}.items():
    room_tag(k, x, y, rotate=rot, size=5.2)
p = P(gcx, gcy - 4.8)
svg.text(*p, "COURT", size=pt(6), family=COND, weight=600, anchor="middle", spacing=1.6)
svg.text(p[0], p[1] + pt(5), "RAKED GRAVEL ABOUT ONE STONE", size=pt(4.2), family=COND, anchor="middle", spacing=0.4)
p = P(sx0 + SS / 2, sy0 + SS / 2 + 1.0)
svg.text(*p, "STAIR HALL", size=pt(6), family=COND, weight=600, anchor="middle", spacing=1.6)
svg.text(p[0], p[1] + pt(5), "OPEN TO ABOVE AND BELOW", size=pt(4.2), family=COND, anchor="middle", spacing=0.4)


def door_tag(key, x, y, color=INK):
    cx, cy = P(x, y)
    r = 7.2
    pts = [(cx + r * math.cos(math.pi / 6 + i * math.pi / 3), cy + r * math.sin(math.pi / 6 + i * math.pi / 3)) for i in range(6)]
    svg.poly(pts, w=mm(0.18), fill=WHITE, closed=True, color=color)
    svg.text(cx, cy + 2.2, key, size=pt(4.4 if len(key) < 4 else 3.6), family=COND, weight=600, anchor="middle", color=color)


def tag_at_door(g, nudge=(0.0, 0.0), color=INK):
    A = B.rooms[g.a]
    d, hw, loc = door_world(g.a, g.da)
    x, y = world(g.a, *loc(F(g.wall) / 2, 0))
    door_tag(g.key, x + nudge[0], y + nudge[1], color=color)


NUDGE = {"D01": (1.6, -2.4), "D02": (0, -2.4), "D03": (0, -2.4), "D04": (0, -2.6), "D05": (1.4, -1.4),
         "HALL": (0, -1.6), "D07": (-2.1, 0), "D08": (2.0, 0), "D09": (2.0, 0), "D10": (2.0, 0),
         "D11": (2.0, 0), "D12": (0, 2.0), "D13": (0, -2.0)}
for g in B.gluings:
    if g.key in NUDGE:
        tag_at_door(g, NUDGE[g.key], color=RED if g.key in B.seams else INK)
door_tag("F4", sx0 + 2.0, sy0 + 5.3, color=RED)
door_tag("C5", 7.1, 29.5, color=RED)


# ----------------------------------------------------------------------------- 9. grid
GX = [("A", -0.375), ("B", 18.25), ("C", 34.75), ("D", 57.25), ("E", 67.75), ("F", 84.375)]
GY = [("1", -0.375), ("2", 20.25), ("3", 25.75), ("4", 47.75 + 0.25), ("5", 63.75), ("6", 78.375)]
top_y, left_x = 86.0, -8.5
REACH_Y = {"A": 80, "B": 80, "C": 80, "D": 50, "E": 28, "F": 28}
REACH_X = {"1": 87, "2": 87, "3": 87, "4": 62.5, "5": 50.0, "6": 32.5}
for lab, x in GX:
    top = lab in "ABCD"
    y0, y1 = (-9.6, top_y - 1.6) if top else (-11.2 + 1.6, REACH_Y[lab])
    svg.line(*P(x, y0), *P(x, y1 if top else REACH_Y[lab]), w=mm(0.09), color=FAINT, dash="14,3,2,3")
    q = P(x, top_y) if top else P(x, -11.2)
    svg.circle(*q, 15, sw=mm(0.25), fill=WHITE)
    svg.text(q[0], q[1] + 5.5, lab, size=pt(11), family=TITLE, weight=700, anchor="middle")
for lab, y in GY:
    svg.line(*P(left_x + 1.6, y), *P(REACH_X[lab], y), w=mm(0.09), color=FAINT, dash="14,3,2,3")
    q = P(left_x, y)
    svg.circle(*q, 15, sw=mm(0.25), fill=WHITE)
    svg.text(q[0], q[1] + 5.5, lab, size=pt(11), family=TITLE, weight=700, anchor="middle")

# ----------------------------------------------------------------------------- 10. dimensions
south = [0, 18, 18.5, 34.5, 35, 57, 57.5, 67.5, 68, 84]
for a, b_ in zip(south, south[1:]):
    dim(svg, *P(a, -0.75), *P(b_, -0.75), fmt_len(round((b_ - a) * 48)), off=50)
dim(svg, *P(0, -0.75), *P(84, -0.75), "84′-0″", off=78)

# The hall, measured along its own floor, and the rooms beside it.
hall_end = 18.5 + F(B.rooms["COR"].w)
for a, b_, col in [(18.5, hall_end, RED)]:
    dim(svg, *P(a, 21.6), *P(b_, 21.6), "38′-6¼″  (MEASURED ALONG THE HALL)", off=0, color=col, ext=False)
q = P(hall_end, 21.6)
svg.text(q[0] + 4, q[1] + 16, "WALL: 5¾″ (SHOULD BE 6″)", size=pt(4.6), family=COND, weight=600, color=RED)
west = [0, 25.5, 26, 63.5, 64, 78]
for a, b_ in zip(west, west[1:]):
    dim(svg, *P(-0.75, a), *P(-0.75, b_), fmt_len(round((b_ - a) * 48)), off=-46)
dim(svg, *P(-0.75, 0), *P(-0.75, 78), "78′-0″", off=-74)
east = [0, 25.5, 26, 47.75]
for a, b_ in zip(east, east[1:]):
    dim(svg, *P(84.75 if b_ <= 25.5 else 60.5, a), *P(84.75 if b_ <= 25.5 else 60.5, b_),
        fmt_len(round((b_ - a) * 48)), off=40 if b_ <= 25.5 else 36)
north = [0, 14.5, 15, 30, 30.5, 37.5]
for a, b_ in zip(north, north[1:]):
    dim(svg, *P(a, 78.75), *P(b_, 78.75), fmt_len(round((b_ - a) * 48)), off=-36)


# ----------------------------------------------------------------------------- 11. redlines
def redline_label(x, y, lines, size=5.2, anchor="start"):
    for i, s in enumerate(lines):
        svg.text(x, y + i * pt(size) * 1.18, s, size=pt(size), family=COND, weight=600, color=RED, anchor=anchor)


def delta(x, y, n):
    pts = [(x, y - 11), (x + 10, y + 7), (x - 10, y + 7)]
    svg.poly(pts, w=mm(0.3), color=RED, fill=WHITE, closed=True)
    svg.text(x, y + 4.5, str(n), size=pt(6), family=TITLE, weight=700, anchor="middle", color=RED)


# I. stair hall
a = P(sx0 - 0.25, sy0 + SS + 1.0)
b_ = P(sx0 + SS + 1.0, sy0 - 0.25)
cloud(svg, a[0], a[1], b_[0], b_[1], r=9)
delta(b_[0] + 2, a[1] - 2, 1)
# II. Gallery V
g1 = bbox(room_poly("G1"))
a, b_ = P(g1[0] - 0.4, g1[3] + 0.4), P(g1[2] + 0.4, g1[1] - 0.4)
svg.poly(S([(g1[0], g1[1]), (g1[2], g1[1]), (g1[2], g1[3]), (g1[0], g1[3])]), w=mm(0.35), color=RED,
         dash="7,4", closed=True)
redline_label(P(19.5, 0)[0], P(0, 31.4)[1], ["GALLERY V"], size=5.2, anchor="middle")
cloud(svg, P(6.4, 0)[0], P(0, 34.0)[1], P(37.4, 0)[0], P(0, 25.65)[1], r=8)
delta(P(6.4, 0)[0] - 4, P(0, 34.0)[1] - 2, 2)
# III. the hall's east end
a, b_ = P(53.2, 26.1), P(60.0, 19.6)
cloud(svg, a[0], a[1], b_[0], b_[1], r=8)
delta(b_[0] + 5, b_[1] + 3, 3)

# ----------------------------------------------------------------------------- inspector's notes
def inspector_notes(x, y):
    svg.text(x, y, "INSPECTOR’S NOTES", size=pt(9), family=TITLE, weight=700, color=RED, spacing=1.5)
    svg.line(x, y + 5, x + 380, y + 5, w=mm(0.35), color=RED)
    notes = [
        ("1", ["THE STAIR CLIMBS FOUR STOREYS, 38′-8″, AND ARRIVES ON", "THE LANDING IT LEFT. THE UP ARROW HAS NO END.", "DOORWAY F4. SEE DETAIL A AND THE DEVELOPED SECTION."]),
        ("2", ["FIVE GALLERIES, EACH TURNING RIGHT, ENCLOSE ONE SQUARE", "COURT: 450° OF TURNING WHERE A CLOSED WALK ALLOWS 360°.", "GALLERY V OCCUPIES THE PLACE OF GALLERY I. DOORWAY C5."]),
        ("3", ["THE HALL IS 38′-6¼″ LONG. THE DINING ROOM, THE WALL", "AND THE LIVING ROOM BESIDE IT MEASURE 38′-6″.", "DOORWAY HALL. SEE DETAIL C (FULL SIZE)."]),
    ]
    yy = y + 30
    for n, lines in notes:
        delta(x + 10, yy - 3, n)
        for i, line in enumerate(lines):
            svg.text(x + 30, yy + i * pt(6.4), line, size=pt(5.6), family=COND, weight=600, color=RED)
        yy += pt(6.4) * len(lines) + 16
    svg.text(x, yy + 4, "EVERY ROOM PASSES INSPECTION. THE HOUSE DOES NOT EXIST.", size=pt(6.2), family=COND,
             weight=700, color=RED, spacing=0.4)


inspector_notes(P(51.5, 0)[0], P(0, 76.0)[1])


# compass carried once around the cloister
def north_arrow(cx, cy, ang_deg, color=INK, label="N", dash=None, solid=True):
    a = math.radians(ang_deg)
    L = 34
    tip = (cx + L * math.sin(a), cy - L * math.cos(a))
    l1 = (cx + 11 * math.sin(a - 2.4), cy - 11 * math.cos(a - 2.4))
    r1 = (cx + 11 * math.sin(a + 2.4), cy - 11 * math.cos(a + 2.4))
    svg.poly([tip, l1, (cx, cy), r1], w=mm(0.25), color=color, fill=color if solid else "none", closed=True, dash=dash)
    lp = (cx + (L + 10) * math.sin(a), cy - (L + 10) * math.cos(a) + 4)
    svg.text(*lp, label, size=pt(8), family=TITLE, weight=700, anchor="middle", color=color)


NX, NY = P(53.5, 0)[0], P(0, 54.5)[1]
svg.circle(NX, NY, 30, sw=mm(0.18))
north_arrow(NX, NY, 0)
north_arrow(NX, NY, 90, color=RED, label="N", solid=False, dash="3,2")
svg.text(NX + 50, NY - 8, "TRUE NORTH", size=pt(5.2), family=COND, weight=600)
svg.text(NX + 50, NY + 2, "NORTH, AFTER ONE CIRCUIT", size=pt(5.2), family=COND, weight=600, color=RED)
svg.text(NX + 50, NY + 11, "OF THE CLOISTER", size=pt(5.2), family=COND, weight=600, color=RED)


# ----------------------------------------------------------------------------- 12. plan title & scale
def drawing_title(x, y, num, title, scale, width=560):
    svg.circle(x + 26, y - 6, 26, sw=mm(0.5))
    svg.line(x, y - 6, x + 52, y - 6, w=mm(0.25))
    svg.text(x + 26, y - 12, num, size=pt(11), family=TITLE, weight=700, anchor="middle")
    svg.text(x + 26, y + 10, "A-101", size=pt(5.5), family=COND, weight=600, anchor="middle")
    svg.text(x + 66, y - 6, title, size=pt(15), family=TITLE, weight=700, spacing=2)
    svg.line(x + 66, y + 2, x + width, y + 2, w=mm(0.5))
    svg.text(x + 66, y + 16, scale, size=pt(6.2), family=COND, weight=500, spacing=0.6)


drawing_title(80, 1336, "1", "LEVEL 1 PLAN", "SCALE: 1/8″ = 1′-0″   ·   ROOMS DRAWN IN PLACE, ROOM BY ROOM, FROM THE FRONT DOOR", 1000)
# scale bar
bx, by = P(66.5, 0)[0], P(0, 53.0)[1]
for i, (a, b_) in enumerate([(0, 2), (2, 4), (4, 8), (8, 16)]):
    svg.rect(bx + a * SCALE, by, (b_ - a) * SCALE, 6, sw=mm(0.18), fill=INK if i % 2 == 0 else WHITE)
for v in (0, 4, 8, 16):
    svg.text(bx + v * SCALE, by - 4, f"{v}′", size=pt(5), family=COND, anchor="middle")


def small_title(x, y, letter, title, sub, width=430, color=INK):
    svg.circle(x + 17, y - 5, 17, sw=mm(0.4), color=color)
    svg.text(x + 17, y + 1, letter, size=pt(11), family=TITLE, weight=700, anchor="middle", color=color)
    svg.text(x + 44, y - 4, title, size=pt(9.5), family=TITLE, weight=700, spacing=1.2, color=color)
    svg.line(x + 44, y + 1, x + width, y + 1, w=mm(0.35), color=color)
    svg.text(x + 44, y + 12, sub, size=pt(5.2), family=COND, weight=500, spacing=0.4, color=color)


# ============================================================================= DETAIL A: stair hall
def detail_a(x0, y0):
    s = 18.75                                   # 3/16" = 1'-0"
    ox, oy = x0 + 0.75 * s + 8, y0 + (SS + 0.75) * s

    def Q(x, y):
        return ox + x * s, oy - y * s

    def fl(k, lx, ly):                          # flight-k local -> stair-hall frame
        x, y = rot2(k, lx - SS / 2, ly - SS / 2)
        return x + SS / 2, y + SS / 2

    L, Wf, Fl = F(LANDING), F(FLIGHT_W), F(FLIGHT_L)
    for k in range(4):
        pts = [fl(k, x, y) for x, y in ((-EXT, -EXT), (Fl, -EXT), (Fl, 0), (-EXT, 0))]
        svg.poly([Q(*p) for p in pts], w=0, fill=INK, closed=True)
        pts = [fl(k, x, y) for x, y in ((-EXT, 0), (0, 0), (0, Wf), (-EXT, Wf))]
        svg.poly([Q(*p) for p in pts], w=0, fill=INK, closed=True)
    for k in range(4):
        for i in range(16):
            x = L + i * F(TREAD)
            svg.line(*Q(*fl(k, x, 0)), *Q(*fl(k, x, Wf - 0.5)), w=mm(0.18))
        for y in (Wf - 0.5, Wf):
            svg.line(*Q(*fl(k, L, y)), *Q(*fl(k, Fl, y)), w=mm(0.3))
        svg.poly([Q(*fl(k, x, y)) for x, y in ((L - .5, Wf - .5), (L, Wf - .5), (L, Wf), (L - .5, Wf))],
                 w=0, fill=INK, closed=True)
        # numbered risers on the first flight
        if k == 0:
            for i in range(16):
                x = L + i * F(TREAD) + F(TREAD) / 2
                if i < 15:
                    q = Q(*fl(k, x, 0.45))
                    svg.text(q[0], q[1] + 2, str(i + 1), size=pt(3.6), family=COND, anchor="middle", color=GREY)
    pts = [Q(*fl(k, x, 1.75)) for k in range(4) for x in (2.0, Fl + 2.0)]
    svg.poly(pts + [pts[0]], w=mm(0.3))
    for k in range(4):
        a_, b2 = Q(*fl(k, 9.6, 1.75)), Q(*fl(k, 10.6, 1.75))
        arrowhead(svg, *b2, math.atan2(b2[1] - a_[1], b2[0] - a_[0]), size=12)
    svg.circle(*Q(*fl(0, 2.0, 1.75)), 5, sw=mm(0.3), fill=WHITE)
    labels = [("LEVEL 1", "±0′-0″"), ("LEVEL 2", "+9′-8″"), ("LEVEL 3", "+19′-4″"), ("LEVEL 4", "+29′-0″")]
    for k, (lv, el) in enumerate(labels):
        c = Q(*fl(k, 2.0, 2.0))
        r = 27
        svg.circle(c[0], c[1], r, sw=mm(0.25), fill=WHITE)
        svg.line(c[0] - r, c[1], c[0] + r, c[1], w=mm(0.18))
        svg.text(c[0], c[1] - 6, lv, size=pt(5.2), family=COND, weight=700, anchor="middle")
        svg.text(c[0], c[1] + 12, el, size=pt(5.4), family=COND, weight=600, anchor="middle")
    c = Q(*fl(0, 2.0, 2.0))
    svg.text(c[0] + 36, c[1] - 40, "LEVEL 1 = +38′-8″", size=pt(5.6), family=COND, weight=700, color=RED)
    svg.text(c[0] + 36, c[1] - 30, "ARRIVING FROM FLIGHT IV", size=pt(4.6), family=COND, weight=600, color=RED)
    for k, nm in enumerate(["I", "II", "III", "IV"]):
        a_, b2 = Q(*fl(k, 4.2, 3.0)), Q(*fl(k, 17.0, 3.0))
        ang = math.degrees(math.atan2(b2[1] - a_[1], b2[0] - a_[0]))
        if 90 < ang <= 270 or -270 <= ang < -90:
            a_, b2, ang = b2, a_, ang - 180
        m = ((a_[0] + b2[0]) / 2, (a_[1] + b2[1]) / 2)
        svg.text(m[0], m[1] + 3, f"FLIGHT {nm} · 16R @ 7¼″ · 15T @ 11″", size=pt(4.4), family=COND, weight=600,
                 anchor="middle", rotate=ang, color=RED if nm == "IV" else INK)
    c = Q(SS / 2, SS / 2)
    svg.text(c[0], c[1] - 10, "WELL", size=pt(7), family=COND, weight=700, anchor="middle", spacing=2)
    svg.text(c[0], c[1] + 4, "OPEN ABOVE AND BELOW,", size=pt(5), family=COND, anchor="middle")
    svg.text(c[0], c[1] + 14, "WITHOUT END", size=pt(5), family=COND, anchor="middle")
    svg.text(c[0], c[1] + 36, "SUM OF RISES ABOUT THE WELL", size=pt(5), family=COND, weight=600, anchor="middle", color=RED)
    svg.text(c[0], c[1] + 48, "4 × 9′-8″ = 38′-8″ ≠ 0", size=pt(6.5), family=COND, weight=700, anchor="middle", color=RED)
    p = Q(*fl(3, F(FLIGHT_L) + 0.2, 2.0))
    door_tag("F4", 0, 0, color=RED) if False else None
    cx, cy = Q(*fl(3, 16.2, 5.3))
    r = 9
    pts = [(cx + r * math.cos(math.pi / 6 + i * math.pi / 3), cy + r * math.sin(math.pi / 6 + i * math.pi / 3)) for i in range(6)]
    svg.poly(pts, w=mm(0.25), fill=WHITE, closed=True, color=RED)
    svg.text(cx, cy + 2.6, "F4", size=pt(5), family=COND, weight=700, anchor="middle", color=RED)
    small_title(x0, oy + 0.75 * s + 50, "A", "STAIR HALL", "ENLARGED PLAN · SCALE 3/16″ = 1′-0″", width=440)


detail_a(1300, 92)


# ============================================================================= DETAIL B: cloister
def detail_b(x0, y0):
    s = 9.0
    gs = GS
    ox, oy = x0 + 50, y0 + gs * s + 10

    def Q(x, y):
        return ox + x * s, oy - y * s

    def gal(k, lx, ly):
        """Gallery-k local -> cloister frame (origin at the cloister's south-west corner)."""
        bx_, by_ = -lx + gs / 2, -ly - gs / 2 + F(GAL_W)
        x, y = rot2(-k, bx_, by_)
        return x + gs / 2, y + gs / 2

    L, Wg = F(GAL_L), F(GAL_W)
    for k in range(4):
        pts = [gal(k, x, y) for x, y in ((0, 0), (L, 0), (L, Wg), (0, Wg))]
        svg.poly([Q(*p) for p in pts], w=mm(0.35), fill="#ffffff", closed=True)
    pts = [gal(4, x, y) for x, y in ((0.25, 0.25), (L - 0.25, 0.25), (L - 0.25, Wg - 0.25), (0.25, Wg - 0.25))]
    svg.poly([Q(*p) for p in pts], w=mm(0.4), color=RED, closed=True, dash="6,3")
    # the walk: five galleries, each turning right, drawn as it is walked
    offs = [4.6, 4.05, 3.5, 2.95, 2.4, 1.85]

    def centre(k):
        a_, b2 = gal(k, 0, offs[k]), gal(k, L, offs[k])
        return a_, b2

    verts = [gal(0, 3.5, offs[0])]
    for k in range(5):
        (a1, b1), (a2, b2) = centre(k), centre(k + 1)
        if abs(a1[1] - b1[1]) < 1e-6:          # gallery k runs east-west
            verts.append((a2[0], a1[1]))
        else:
            verts.append((a1[0], a2[1]))
    stub = gal(5, 6.0, offs[5])
    pts = [Q(*p) for p in verts]
    svg.poly(pts[:5], w=mm(0.3))
    svg.poly(pts[4:] + [Q(*stub)], w=mm(0.4), color=RED)
    arrowhead(svg, *Q(*stub), math.atan2(Q(*stub)[1] - pts[-1][1], Q(*stub)[0] - pts[-1][0]), size=11, color=RED)
    st = pts[0]
    svg.circle(*st, 4.5, sw=mm(0.3), fill=WHITE)
    arrowhead(svg, st[0] - 16, st[1], math.pi, size=10)
    svg.line(st[0] - 4, st[1], st[0] - 14, st[1], w=mm(0.35))
    for k in range(5):
        if k == 0:
            q = Q(*gal(0, L / 2, Wg + 2.2))
            svg.text(q[0] - 14, q[1] + 6, "I", size=pt(8), family=TITLE, weight=700, anchor="middle")
            svg.text(q[0], q[1] + 6, "/", size=pt(8), family=TITLE, weight=700, anchor="middle", color=GREY)
            svg.text(q[0] + 14, q[1] + 6, "V", size=pt(8), family=TITLE, weight=700, anchor="middle", color=RED)
            continue
        if k == 4:
            continue
        q = Q(*gal(k, L / 2, Wg / 2 + 1.2))
        svg.text(q[0], q[1] + 4, ["I", "II", "III", "IV", "V"][k], size=pt(8),
                 family=TITLE, weight=700, anchor="middle")
    for k in range(5):
        c = pts[k + 1]
        dx = -14 if k in (0, 4) else 14
        c = (c[0] + (dx if k != 4 else -14), c[1] + (-14 if k in (1, 2) else 14) + (16 if k == 4 else 0))
        svg.circle(c[0], c[1], 7.5, sw=mm(0.25), fill=WHITE, color=RED if k == 4 else INK)
        svg.text(c[0], c[1] + 3, str(k + 1), size=pt(5.6), family=COND, weight=700, anchor="middle",
                 color=RED if k == 4 else INK)
    q = Q(*gal(0, 2.0, -1.4))
    svg.text(q[0], q[1] + 4, "START: GALLERY I,", size=pt(4.8), family=COND, weight=600, anchor="end")
    svg.text(q[0], q[1] + 13, "WALKING WEST", size=pt(4.8), family=COND, weight=600, anchor="end")
    q = Q(*gal(5, 9.0, offs[5]))
    svg.text(q[0] + 14, q[1] - 2, "HOME: GALLERY I AGAIN,", size=pt(4.8), family=COND, weight=700, color=RED)
    svg.text(q[0] + 14, q[1] + 7, "BUT WALKING NORTH", size=pt(4.8), family=COND, weight=700, color=RED)
    # the stone, and the quarter turn about it
    c = Q(gs / 2, gs / 2)
    svg.circle(*c, 9, sw=mm(0.35), fill=WHITE)
    R = 38
    arc = [(c[0] + R * math.cos(math.radians(a)), c[1] - R * math.sin(math.radians(a))) for a in range(100, 0, -3)]
    svg.poly(arc, w=mm(0.4), color=RED)
    arrowhead(svg, *arc[-1], math.atan2(arc[-1][1] - arc[-2][1], arc[-1][0] - arc[-2][0]), size=10, color=RED)
    svg.text(c[0] + 2, c[1] + 26, "90°", size=pt(8), family=TITLE, weight=700, anchor="middle", color=RED)
    svg.text(c[0], c[1] - 46, "5 TURNS × 90° = 450°", size=pt(6), family=COND, weight=700, anchor="middle", color=RED)
    svg.text(c[0], c[1] + 52, "A WALK ONCE ROUND THE COURT", size=pt(4.8), family=COND, weight=600, anchor="middle")
    svg.text(c[0], c[1] + 61, "COMES HOME A QUARTER-TURN", size=pt(4.8), family=COND, weight=600, anchor="middle")
    svg.text(c[0], c[1] + 70, "ABOUT THE STONE", size=pt(4.8), family=COND, weight=600, anchor="middle")
    small_title(x0, oy + 52, "B", "CLOISTER OF FIVE CORNERS", "DIAGRAM · SCALE 3/32″ = 1′-0″ · GALLERY V DRAWN IN RED", width=440)


detail_b(1300, 625)


# ============================================================================= DETAIL C: full size
def detail_c(x0, y0):
    ppi = U                                     # full size
    start = 459.55
    w_in = 4.1
    top = y0 + 72
    h = 0.9 * ppi

    def X(inch):
        return x0 + (inch - start) * ppi

    # floorboards of the hall, in section-like plan: the hall's floor ends at its own east face
    svg.rect(X(start), top, (462.25 - start) * ppi, h, sw=0, fill="#f1ede4")
    # the tape blade
    svg.rect(X(start), top + 18, w_in * ppi, 0.5 * ppi, sw=mm(0.25), fill="#ffffff")
    i = 0
    x16 = math.ceil(start * 16)
    while x16 / 16 <= start + w_in:
        inch = x16 / 16
        L = 22 if x16 % 16 == 0 else 15 if x16 % 8 == 0 else 11 if x16 % 4 == 0 else 7 if x16 % 2 == 0 else 4.5
        svg.line(X(inch), top + 18, X(inch), top + 18 + L, w=mm(0.18) if x16 % 16 else mm(0.3))
        if x16 % 16 == 0:
            svg.text(X(inch) - 3, top + 18 + 40, str(int(inch)), size=pt(10), family=TITLE, weight=700, anchor="end")
        x16 += 1
    # the two faces
    room_face = 462.0
    hall_face = 462.25
    svg.rect(X(room_face), top - 30, (hall_face - room_face) * ppi, h + 70, sw=0, fill=RED, opacity=0.16)
    svg.line(X(room_face), top - 34, X(room_face), top + h + 44, w=mm(0.5))
    svg.line(X(hall_face), top - 34, X(hall_face), top + h + 44, w=mm(0.5), color=RED)
    svg.text(X(room_face) - 6, top - 22, "38′-6″", size=pt(8), family=TITLE, weight=700, anchor="end")
    svg.text(X(room_face) - 6, top - 12, "BY THE ROOMS", size=pt(5), family=COND, weight=600, anchor="end")
    svg.text(X(hall_face) + 6, top - 22, "38′-6¼″", size=pt(8), family=TITLE, weight=700, color=RED)
    svg.text(X(hall_face) + 6, top - 12, "BY THE HALL", size=pt(5), family=COND, weight=600, color=RED)
    dim(svg, X(room_face), top + h + 30, X(hall_face), top + h + 30, "", off=0, color=RED, ext=False)
    svg.text((X(room_face) + X(hall_face)) / 2, top + h + 54, "¼″", size=pt(13), family=TITLE, weight=700,
             anchor="middle", color=RED)
    svg.text(x0, top + h + 54, "AT FULL SIZE, THE", size=pt(5.2), family=COND, weight=600)
    svg.text(x0, top + h + 63, "DEFECT IS THIS WIDE:", size=pt(5.2), family=COND, weight=600)
    small_title(x0, y0 + 14, "C", "THE HALL AT THE ENTRANCE", "FULL SIZE · 1 : 1 WHEN PRINTED AT 18 × 24 IN", width=440)


detail_c(1300, 1068)


# ============================================================================= DEVELOPED SECTION
def developed_section(x0, y0):
    s = 9.375                                   # 3/32" = 1'-0"
    base_y = y0 + 520
    lab_w = 150
    ox = x0 + lab_w
    Fl = F(FLIGHT_L)
    Sto = F(STOREY)
    R, T = F(RISER), F(TREAD)
    Lnd = F(LANDING)
    SLAB, WAIST = 0.75, 0.55

    def Q(u, z):
        return ox + u * s, base_y - z * s

    names = ["I", "II", "III", "IV", "I"]
    for j in range(5):
        u0, z0 = j * Fl, j * Sto
        top = [(0.0, 0.0), (Lnd, 0.0)]
        for i in range(15):
            x = Lnd + i * T
            top += [(x, (i + 1) * R), (x + T, (i + 1) * R)]
        top.append((Fl, Sto))
        xs = Lnd - (SLAB - WAIST) / (R / T)
        prof = top + [(Fl, Sto - SLAB), (Fl, (Fl - Lnd) * R / T - WAIST), (xs, -SLAB), (0.0, -SLAB)]
        pts = [Q(u0 + x, z0 + z) for x, z in prof]
        ghost = j == 4
        if ghost:
            svg.poly(pts, w=mm(0.35), color=RED, fill="#ffffff", closed=True, dash="6,3")
        else:
            cp = svg.clip_poly(pts)
            svg.poly(pts, w=mm(0.35), fill="#ffffff", closed=True)
            # concrete hatch: stipple and small triangles
            random.seed(j)
            svg.open(clip_path=cp)
            xs_, ys_ = [p[0] for p in pts], [p[1] for p in pts]
            for _ in range(260):
                px, py = random.uniform(min(xs_), max(xs_)), random.uniform(min(ys_), max(ys_))
                if random.random() < 0.25:
                    a = random.uniform(0, 6.28)
                    tri = [(px + 3.2 * math.cos(a + t), py + 3.2 * math.sin(a + t)) for t in (0, 2.1, 4.2)]
                    svg.poly(tri, w=mm(0.09), color=GREY, closed=True)
                else:
                    svg.circle(px, py, 0.7, sw=0, fill=GREY)
            svg.close()
        # doorway tag at the junction
        if j < 4:
            q = Q(u0 + Fl, z0 + Sto + 2.6)
            cx, cy = q
            r = 8
            hexp = [(cx + r * math.cos(math.pi / 6 + i * math.pi / 3), cy + r * math.sin(math.pi / 6 + i * math.pi / 3)) for i in range(6)]
            red = j == 3
            svg.poly(hexp, w=mm(0.25), fill=WHITE, closed=True, color=RED if red else INK)
            svg.text(cx, cy + 2.5, f"F{j+1}", size=pt(4.6), family=COND, weight=700, anchor="middle",
                     color=RED if red else INK)
        q = Q(u0 + Fl / 2 + 1.5, z0 + Sto / 2 - 2.6)
        svg.text(q[0], q[1], f"FLIGHT {names[j]}", size=pt(5.4), family=COND, weight=700,
                 rotate=-math.degrees(math.atan(R / T)), color=RED if ghost else INK)
    # datum lines
    levels = [(0, "LEVEL 1", "±0′-0″", INK), (1, "LEVEL 2", "+9′-8″", INK), (2, "LEVEL 3", "+19′-4″", INK),
              (3, "LEVEL 4", "+29′-0″", INK), (4, "LEVEL 1", "+38′-8″", RED)]
    for n, lv, el, col in levels:
        y = base_y - n * Sto * s
        svg.line(x0 + 34, y, ox + 5 * Fl * s + 10, y, w=mm(0.13), color=col, dash="18,4,3,4")
        cx = x0 + 16
        svg.circle(cx, y, 9, sw=mm(0.25), color=col, fill=WHITE)
        svg.path(f"M{cx},{y - 9} A9,9 0 0 1 {cx + 9},{y} L{cx},{y} Z", sw=0, fill=col)
        svg.path(f"M{cx},{y + 9} A9,9 0 0 1 {cx - 9},{y} L{cx},{y} Z", sw=0, fill=col)
        svg.text(x0 + 34, y - 5, lv, size=pt(6.2), family=COND, weight=700, color=col)
        svg.text(x0 + 34 + 44, y - 5, el, size=pt(6.2), family=COND, weight=500, color=col)
    # identification: the first landing and the last are the same landing
    a = Q(Lnd / 2, 0.0)
    b2 = Q(4 * Fl + Lnd / 2, 4 * Sto)
    for (px, py) in (a, b2):
        for d_ in (-5, 4):
            svg.poly([(px + d_ - 5, py + 10), (px + d_, py + 16), (px + d_ - 5, py + 22)], w=mm(0.4), color=RED)
    ctrl = (a[0] + 60, b2[1] - 10)
    svg.path(f"M{a[0]},{a[1] - 4} C{a[0]},{a[1] - 220} {ctrl[0]},{ctrl[1]} {b2[0] - 20},{b2[1] - 6}",
             stroke=RED, sw=mm(0.3), dash="5,4")
    arrowhead(svg, b2[0] - 20, b2[1] - 6, math.atan2(-6 - (ctrl[1] - b2[1]), -20 - (ctrl[0] - b2[0])) * 0 + 0.05, size=9, color=RED)
    svg.text(a[0] + 64, b2[1] + 44, "THE SAME LANDING", size=pt(7.5), family=TITLE, weight=700, color=RED, spacing=1)
    svg.text(a[0] + 64, b2[1] + 56, "IDENTIFY THESE TWO EDGES, AS ONE GLUES THE SIDES OF A TORUS", size=pt(5.2),
             family=COND, weight=600, color=RED)
    # total rise
    xr = ox + 5 * Fl * s + 26
    dim(svg, xr, base_y, xr, base_y - 4 * Sto * s, "", off=0, color=RED, ext=False)
    svg.text(xr + 10, base_y - 2 * Sto * s - 6, "38′-8″", size=pt(10), family=TITLE, weight=700, color=RED)
    svg.text(xr + 10, base_y - 2 * Sto * s + 8, "= 0′-0″", size=pt(10), family=TITLE, weight=700, color=RED)
    svg.text(x0 + 2, base_y + 52, "UNFOLDED", size=pt(5), family=COND, weight=600, color=GREY)


developed_section(80, 1360)
drawing_title(80, 1990, "2", "STAIR HALL — DEVELOPED SECTION",
              "THE FOUR WALLS OF THE STAIR HALL UNFOLDED INTO ONE PLANE   ·   SCALE: 3/32″ = 1′-0″", 1080)


# ============================================================================= ROOM SCHEDULE
def schedule(x0, y0, width=560):
    rows = [("LIB", ""), ("DIN", ""), ("LIV", ""), ("ENT", "FRONT DOOR ON HOLONOMY LANE"), ("KIT", ""),
            ("COR", "¼″ LONGER THAN THE HOUSE"), ("ST1", "LEVEL 1 TO LEVEL 2"), ("ST2", "LEVEL 2 TO LEVEL 3"),
            ("ST3", "LEVEL 3 TO LEVEL 4"), ("ST4", "LEVEL 4 TO LEVEL 1"), ("G1", "TURNS RIGHT INTO GALLERY II"),
            ("G2", "TURNS RIGHT INTO GALLERY III"), ("G3", "TURNS RIGHT INTO GALLERY IV"),
            ("G4", "TURNS RIGHT INTO GALLERY V"), ("G5", "IN THE PLACE OF GALLERY I"), ("BR1", ""), ("BR2", ""),
            ("BTH", "")]
    red = {"COR", "ST4", "G5"}
    cols = [(0, "KEY"), (48, "ROOM"), (240, "AREA"), (300, "CLG"), (356, "REMARKS")]
    rh = 25
    svg.text(x0, y0, "ROOM SCHEDULE", size=pt(9.5), family=TITLE, weight=700, spacing=1.2)
    y = y0 + 12
    svg.line(x0, y, x0 + width, y, w=mm(0.5))
    for cx, lab in cols:
        svg.text(x0 + cx + 2, y + 16, lab, size=pt(5.2), family=COND, weight=700, spacing=0.8)
    y += rh
    svg.line(x0, y, x0 + width, y, w=mm(0.25))
    total = 0.0
    for k, note in rows:
        r = B.rooms[k]
        col = RED if k in red else INK
        a = r.w * r.d / FOOT / FOOT
        total += a
        vals = [k, r.name.upper().replace("STAIR HALL, ", "STAIR ")[:26], f"{a:,.2f}" if k == "COR" else f"{a:,.0f}",
                fmt_len(r.h) if r.kind != "stair" else "OPEN", note]
        for (cx, _), v in zip(cols, vals):
            svg.text(x0 + cx + 2, y + 17, v, size=pt(5.4), family=COND, weight=600 if cx == 0 else 500, color=col)
        y += rh
        svg.line(x0, y, x0 + width, y, w=mm(0.09), color=FAINT)
    svg.line(x0, y, x0 + width, y, w=mm(0.5))
    svg.text(x0 + 50, y + 18, "TOTAL, 18 ROOMS", size=pt(5.6), family=COND, weight=700)
    svg.text(x0 + cols[2][0] + 2, y + 18, f"{total:,.2f} SF", size=pt(5.6), family=COND, weight=700)
    svg.text(x0 + cols[4][0] + 2, y + 18, "OF WHICH 210 SF IS COUNTED TWICE", size=pt(5.4), family=COND,
             weight=600, color=RED)


schedule(1180, 1372)


# ============================================================================= TITLE BLOCK & BORDER
svg.rect(50, 50, 1700, 2300, sw=mm(0.7))
svg.rect(58, 58, 1684, 2284, sw=mm(0.18))
TB = 2052
svg.line(58, TB, 1742, TB, w=mm(0.7))
for x in (640, 1010, 1270):
    svg.line(x, TB, x, 2342, w=mm(0.35))


def tb_label(x, y, s):
    svg.text(x, y, s, size=pt(4.6), family=COND, weight=600, spacing=1.0, color=GREY)


# general notes
tb_label(74, TB + 22, "GENERAL NOTES")
notes = [
    "1.  ALL DIMENSIONS ARE EXACT TO ¼″. DO NOT SCALE DRAWINGS.",
    "2.  EACH ROOM IS DESCRIBED ONLY IN ITS OWN FRAME. NO ROOM KNOWS WHERE THE OTHERS ARE.",
    f"3.  EVERY ROOM COMPLIES WITH THE INTERNATIONAL RESIDENTIAL CODE: {CERT['local_checks']} OF {CERT['local_checks']} CHECKS PASS.",
    "4.  ROOMS ARE DRAWN IN PLACE ALONG A SPANNING TREE FROM THE FRONT DOOR. THREE DOORWAYS,",
    "     F4, C5 AND HALL, CANNOT BE DRAWN IN PLACE. THEY ARE SHOWN IN RED.",
    "5.  BRICK UP ANY ONE OF F1–F4, ONE OF C2–C5, AND ONE OF D01, D02, D03 OR HALL, AND THE HOUSE",
    f"     WILL EXIST. {len(CERT['fixes_three'])} OF THE {CERT['triples_tried']:,} WAYS OF BRICKING UP THREE DOORWAYS WORK. NO TWO DOORWAYS ARE ENOUGH.",
    "6.  CONTRACTOR SHALL VERIFY EXISTENCE BEFORE COMMENCING WORK.",
]
for i, n in enumerate(notes):
    svg.text(74, TB + 48 + i * 31, n, size=pt(5.6), family=COND, weight=500)

# revisions
tb_label(656, TB + 22, "REVISIONS")
revs = [("1", "FLIGHT IV GLUED TO FLIGHT I"), ("2", "GALLERY V GLUED TO GALLERY I"), ("3", "HALL LENGTHENED ¼″")]
for i, (n, txt) in enumerate(revs):
    y = TB + 60 + i * 52
    delta(674, y - 4, n)
    svg.text(698, y, txt, size=pt(6), family=COND, weight=600, color=RED)
    svg.text(698, y + 16, "05 NOV 2026 · BY THE ARCHITECT", size=pt(4.8), family=COND, color=GREY)
svg.text(656, 2318, "ISSUED FOR: EXISTENCE", size=pt(6.2), family=COND, weight=700)
svg.text(656, 2332, "STATUS: REFUSED", size=pt(6.2), family=COND, weight=700, color=RED)

# stamp
cx, cy = 1140, TB + 140
svg.circle(cx, cy, 98, sw=mm(0.6), color=RED)
svg.circle(cx, cy, 88, sw=mm(0.25), color=RED)
svg.text(cx, cy - 30, "NOT FOR", size=pt(10), family=TITLE, weight=700, anchor="middle", color=RED, spacing=2)
svg.text(cx, cy - 6, "CONSTRUCTION", size=pt(12), family=TITLE, weight=700, anchor="middle", color=RED, spacing=1.5)
svg.line(cx - 70, cy + 4, cx + 70, cy + 4, w=mm(0.35), color=RED)
svg.text(cx, cy + 26, "NOT FOR", size=pt(10), family=TITLE, weight=700, anchor="middle", color=RED, spacing=2)
svg.text(cx, cy + 50, "EXISTENCE", size=pt(12), family=TITLE, weight=700, anchor="middle", color=RED, spacing=1.5)

# project
X0 = 1286
tb_label(X0, TB + 22, "PROJECT")
svg.text(X0, TB + 56, "NO. 1 HOLONOMY LANE", size=pt(17), family=TITLE, weight=700, spacing=1.5)
svg.text(X0, TB + 76, "CHARLOTTE, NORTH CAROLINA", size=pt(7), family=COND, weight=600, spacing=1.5)
svg.line(X0, TB + 90, 1726, TB + 90, w=mm(0.25))
tb_label(X0, TB + 108, "SHEET")
svg.text(X0, TB + 128, "LEVEL 1 PLAN · DETAILS · DEVELOPED SECTION", size=pt(6.4), family=COND, weight=700)
rows_ = [("DRAWN", ARTIST.upper()), ("CHECKED", f"Z3 {CERT['z3_version']} — UNSAT"), ("DATE", "05 NOV 2026"),
         ("SCALE", "AS NOTED"), ("CERT.", CERT["sha256"][:16].upper())]
for i, (k, v) in enumerate(rows_):
    y = TB + 156 + i * 24
    tb_label(X0, y, k)
    svg.text(X0 + 60, y, v, size=pt(6), family=COND, weight=600)
svg.line(1600, TB + 90, 1600, 2342, w=mm(0.35))
svg.text(1671, TB + 160, "SHEET", size=pt(5), family=COND, weight=600, anchor="middle", color=GREY, spacing=1)
svg.text(1671, TB + 220, "A-101", size=pt(30), family=TITLE, weight=700, anchor="middle")
svg.text(1671, TB + 250, "1 OF 1", size=pt(5.5), family=COND, weight=600, anchor="middle")


if __name__ == "__main__":
    out = ROOT / "out" / "plates"
    out.mkdir(parents=True, exist_ok=True)
    svg.save(out / "02_floor_plan.svg")
