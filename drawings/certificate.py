"""Plate III — THE CERTIFICATE.

Everything printed here is computed: the counts come from the inspection, the
matrices from multiplying doorway transformations, the serial number from a
SHA-256 hash of the building, the microtext border is the solver's own proof.
"""

from __future__ import annotations

import json
import math
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import qrcode  # noqa: E402

from drawings.svg import SVG, U, pt, mm  # noqa: E402
from drawings.typeset import set_paragraph, width  # noqa: E402
from nonexistence.building import inspect  # noqa: E402
from nonexistence.geometry import Motion, fmt_len  # noqa: E402
from nonexistence.holonomy_lane import build  # noqa: E402

CERT = json.loads((ROOT / "out/proof/certificate.json").read_text())
PROOF = (ROOT / "out/proof/z3_proof.txt").read_text()
B = build()
ARTIST = (ROOT / "ARTIST.txt").read_text().strip() if (ROOT / "ARTIST.txt").exists() else ""

INK = "#1b1a17"
GREEN = "#24524a"
PALE = "#c9d8d0"
RED = "#b8321f"
PEN = "#1e2d5c"
WHITE = "#ffffff"
SERIF = "Baskerville"
DIDOT = "Didot"
MATH = "STIX Two Text"
MONO = "Menlo"

svg = SVG(18, 24)
W, H = svg.W, svg.H
X0, X1 = 250.0, 1550.0          # text column
CX = W / 2


# ============================================================================= guilloché
def band(x0, y0, x1, y1, n=14, amp=15.0, lam=60.0, color=GREEN, w=mm(0.08)):
    """A woven border band along the four sides of a rectangle (centre-line rectangle)."""
    per = 2 * ((x1 - x0) + (y1 - y0))

    def at(s):
        s %= per
        if s < x1 - x0:
            return (x0 + s, y0), (0, -1)
        s -= x1 - x0
        if s < y1 - y0:
            return (x1, y0 + s), (1, 0)
        s -= y1 - y0
        if s < x1 - x0:
            return (x1 - s, y1), (0, 1)
        s -= x1 - x0
        return (x0, y1 - s), (-1, 0)

    k = 2 * math.pi / lam
    steps = int(per / 1.5)
    for fam, (A, kk, nn) in enumerate(((amp, k, n), (amp * 0.55, 2 * k, n // 2))):
        for i in range(nn):
            ph = 2 * math.pi * i / nn
            pts = []
            for j in range(steps + 1):
                s = per * j / steps
                (px, py), (nx, ny) = at(s)
                o = A * math.sin(kk * s + ph) * (0.75 + 0.25 * math.cos(k * s / 5 + ph))
                pts.append((px + nx * o, py + ny * o))
            svg.poly(pts, w=w, color=color)


def rosette(cx, cy, R, a, lobes, copies, color=GREEN, w=mm(0.08), squash=1.0, opacity=None):
    for c in range(copies):
        ph = 2 * math.pi * c / copies / lobes
        pts = []
        for i in range(721):
            t = 2 * math.pi * i / 720
            r = R + a * math.cos(lobes * (t + ph))
            pts.append((cx + r * math.cos(t), cy + r * math.sin(t) * squash))
        svg.poly(pts, w=w, color=color, closed=True, opacity=opacity)


def spirograph(cx, cy, R, r, d, turns, color=GREEN, w=mm(0.07), opacity=None):
    pts = []
    N = 3000
    for i in range(N + 1):
        t = 2 * math.pi * turns * i / N
        x = (R - r) * math.cos(t) + d * math.cos((R - r) / r * t)
        y = (R - r) * math.sin(t) - d * math.sin((R - r) / r * t)
        pts.append((cx + x, cy + y))
    svg.poly(pts, w=w, color=color, opacity=opacity)


# safety-paper background: fine waves across the sheet
clip = svg.clip_rect(210, 210, W - 420, H - 420)
svg.open(clip_path=clip)
for j in range(0, int(H), 7):
    pts = [(x, j + 2.2 * math.sin(x / 23.0 + j / 31.0) + 1.2 * math.sin(x / 7.0 + j)) for x in range(200, int(W) - 199, 6)]
    svg.poly(pts, w=mm(0.05), color="#dfe8e2")
svg.close()

# central medallion, very pale, behind the title and the findings
svg.open(opacity=0.55)
spirograph(CX, 760, 300, 75, 120, 3, color="#cfdcd4", w=mm(0.07))
spirograph(CX, 760, 300, 60, 150, 1, color="#cfdcd4", w=mm(0.07))
svg.close()

# border
band(150, 150, W - 150, H - 150, n=16, amp=18, lam=72)
svg.rect(118, 118, W - 236, H - 236, stroke=GREEN, sw=mm(0.5))
svg.rect(126, 126, W - 252, H - 252, stroke=GREEN, sw=mm(0.12))
svg.rect(174, 174, W - 348, H - 348, stroke=GREEN, sw=mm(0.12))
svg.rect(182, 182, W - 364, H - 364, stroke=GREEN, sw=mm(0.5))
for (cx, cy) in ((150, 150), (W - 150, 150), (150, H - 150), (W - 150, H - 150)):
    svg.circle(cx, cy, 52, color=GREEN, sw=mm(0.5), fill=WHITE)
    rosette(cx, cy, 34, 12, 4, 6)
    rosette(cx, cy, 20, 8, 5, 4, color=RED)
    svg.circle(cx, cy, 4, sw=0, fill=GREEN)
# mid-side medallions: four lobes on the long sides, five on the short
for (cx, cy, lob) in ((CX, 150, 5), (CX, H - 150, 5), (150, H / 2, 4), (W - 150, H / 2, 4)):
    svg.circle(cx, cy, 40, color=GREEN, sw=mm(0.4), fill=WHITE)
    rosette(cx, cy, 26, 9, lob, 6)

# microtext: the solver's proof, run twice round the inner frame
micro = re.sub(r"\s+", " ", PROOF).strip()
ring_text = ("Z3 PROOF OF UNSATISFIABILITY · NO. 1 HOLONOMY LANE · " + micro + " · ")


def micro_ring(inset, text, size=pt(3.0)):
    cw = width("0", MONO, size)
    x0, y0, x1, y1 = inset, inset, W - inset, H - inset
    sides = [((x0, y0), 0, x1 - x0), ((x1, y0), 90, y1 - y0), ((x1, y1), 180, x1 - x0), ((x0, y1), 270, y1 - y0)]
    pos = 0
    for (sx, sy), rot, L in sides:
        n = int(L / cw)
        chunk = (text * 3)[pos:pos + n]
        pos += n
        svg.text(sx, sy, chunk, size=size, family=MONO, color=GREEN, rotate=rot, baseline="text-after-edge")
    return pos


used = micro_ring(198, ring_text)
micro_ring(206, ring_text[used:] + ring_text)


# ============================================================================= header
def caps(x, y, s, size, family=DIDOT, spacing=6, color=INK, anchor="middle", weight=400):
    svg.text(x, y, s, size=size, family=family, weight=weight, anchor=anchor, spacing=spacing, color=color)


caps(CX, 282, "BUREAU OF EUCLIDEAN INSPECTION", pt(13), family="Copperplate", spacing=5, color=GREEN)
caps(CX, 308, "DIVISION OF EXISTENCE  ·  FORM N-1  ·  ISSUED UNDER THE ELEMENTS, BOOK I, POSTULATES 1–5",
     pt(6.5), family="Copperplate", spacing=1.6, color=GREEN)

serial = CERT["sha256"][:16].upper()
serial_fmt = " ".join(serial[i:i + 4] for i in range(0, 16, 4))
svg.text(X1, 252, f"No. {serial_fmt}", size=pt(9), family=MONO, weight=700, anchor="end", color=RED, spacing=1.5)
svg.text(X0, 252, "PROPERTY  01", size=pt(7), family=MONO, weight=700, color=GREEN, spacing=1.5)

caps(CX, 470, "CERTIFICATE", pt(76), family=DIDOT, spacing=14)
svg.text(CX, 548, "of Nonexistence", size=pt(40), family=DIDOT, italic=True, anchor="middle", color=INK)
svg.line(CX - 230, 580, CX - 30, 580, w=mm(0.3), color=GREEN)
svg.line(CX + 30, 580, CX + 230, 580, w=mm(0.3), color=GREEN)
svg.poly([(CX, 572), (CX + 8, 580), (CX, 588), (CX - 8, 580)], w=0, fill=GREEN, closed=True)

# ============================================================================= certifying text
y = 640
svg.text(CX, y, "This is to certify that the property known as", size=pt(15), family=SERIF, italic=True,
         anchor="middle")
y += 62
caps(CX, y, "No. 1 HOLONOMY LANE", pt(30), family=DIDOT, spacing=6)
y += 34
caps(CX, y, "CHARLOTTE  ·  NORTH CAROLINA", pt(8), family="Copperplate", spacing=4, color=GREEN)
y += 48
body = ("comprising eighteen rooms joined by twenty-two doorways, has been inspected room by room and found "
        "sound in every room; and that the said property has been proved, by a method any reader may "
        "repeat, not to exist.")
y = set_paragraph(svg, X0 + 120, y, (X1 - X0) - 240, body, SERIF, pt(14), pt(19.5), italic=False,
                  justify=False, align="center")

# ============================================================================= inspection record
y += 18
svg.line(X0, y, X1, y, w=mm(0.5), color=GREEN)
svg.line(X0, y + 5, X1, y + 5, w=mm(0.12), color=GREEN)
caps(CX, y + 30, "RECORD OF INSPECTION", pt(8), family="Copperplate", spacing=4, color=GREEN)
groups = defaultdict(lambda: [0, 0, ""])
for f in inspect(B):
    key = (f.item, f.section)
    groups[key][0] += f.ok
    groups[key][1] += 1
order = [("Ceiling height, habitable space", "R305.1"), ("Egress door clear width", "R311.2"),
         ("Egress door clear height", "R311.2"), ("Hallway width", "R311.6"), ("Stair width", "R311.7.1"),
         ("Stair headroom", "R311.7.2"), ("Riser height", "R311.7.5.1"), ("Tread depth", "R311.7.5.2"),
         ("Doorway leaves match", "—")]
rows = [(lbl, sec, *groups[(lbl, sec)][:2]) for lbl, sec in order]
colw = (X1 - X0 - 60) / 2
ry = y + 62
for i, (lbl, sec, ok, n) in enumerate(rows + [("EXISTENCE", "—", 0, 1)]):
    col, row = divmod(i, 5)
    x = X0 + col * (colw + 60)
    yy = ry + row * 31
    last = lbl == "EXISTENCE"
    left = lbl if sec == "—" else f"{lbl}  ({sec})"
    if last:
        left = "Existence"
    svg.text(x, yy, left, size=pt(10.5), family=SERIF, weight=600 if last else 400, color=RED if last else INK)
    res = "FAILED" if last else f"PASSED  {ok} / {n}"
    svg.text(x + colw, yy, res, size=pt(8.5), family="Copperplate", weight=700 if last else 400,
             anchor="end", color=RED if last else GREEN, spacing=1.5)
    lw = width(left, SERIF, pt(10.5), 600 if last else 400)
    rw = width(res, "Copperplate", pt(8.5), 700 if last else 400, spacing=1.5)
    dx = x + lw + 10
    while dx < x + colw - rw - 10:
        svg.circle(dx, yy - 3, 0.9, sw=0, fill=RED if last else INK)
        dx += 7
y = ry + 5 * 31 - 8
svg.line(X0, y, X1, y, w=mm(0.12), color=GREEN)
svg.line(X0, y + 5, X1, y + 5, w=mm(0.5), color=GREEN)

# ============================================================================= the line
y += 66
svg.text(CX, y, "The property has passed every inspection except existence.", size=pt(25), family=DIDOT,
         italic=True, anchor="middle")

# ============================================================================= findings
y += 52
caps(CX, y, "FINDINGS", pt(9), family="Copperplate", spacing=6, color=GREEN)
svg.line(X0, y - 4, CX - 90, y - 4, w=mm(0.15), color=GREEN)
svg.line(CX + 90, y - 4, X1, y - 4, w=mm(0.15), color=GREEN)
FY = y + 30
gap = 40
fw = (X1 - X0 - 2 * gap) / 3


def matrix(x, y, M, size=pt(9.5), color=INK, highlight=()):
    """Typeset a 4×4 integer matrix with brackets. Returns its width."""
    cw = [max(width(str(M[r][c]), MATH, size) for r in range(4)) + 16 for c in range(4)]
    rh = size * 1.18
    h = rh * 4
    total = sum(cw) + 12
    br = 6
    svg.poly([(x + br, y), (x, y), (x, y + h), (x + br, y + h)], w=mm(0.3), color=color)
    svg.poly([(x + total - br, y), (x + total, y), (x + total, y + h), (x + total - br, y + h)], w=mm(0.3), color=color)
    cx = x + 6
    for c in range(4):
        for r in range(4):
            v = M[r][c]
            col = RED if (r, c) in highlight else color
            svg.text(cx + cw[c] / 2, y + rh * (r + 0.78), str(v).replace("-", "−"), size=size, family=MATH,
                     anchor="middle", color=col)
        cx += cw[c]
    return total, h


def subscripted(x, y, base, subs, size=pt(10.5), color=INK):
    cx = x
    for s in subs:
        svg.text(cx, y, base, size=size, family=MATH, italic=True, color=color)
        cx += width(base, MATH, size, italic=True) + 1
        svg.text(cx, y + size * 0.28, s, size=size * 0.62, family=MATH, color=color)
        cx += width(s, MATH, size * 0.62) + 5
    return cx


loops = {L["seam"]: L for L in CERT["loops"]}
finds = [
    ("I", "THE STAIR HALL", "F4",
     "Four flights, each climbing one storey, arrive on the landing where the first began.",
     "a rise of thirty-eight feet eight inches, where any closed walk must rise not at all.", {(2, 3)}),
    ("II", "THE CLOISTER", "C5",
     "Five galleries, each turning right, enclose a single square court.",
     "a turn of four hundred and fifty degrees, where any closed walk must turn three hundred and sixty.", {(0, 0), (0, 1), (1, 0), (1, 1)}),
    ("III", "THE HALL", "HALL",
     "The hall measures a quarter inch longer than the rooms that run beside it.",
     "a gap of one quarter of an inch, where any closed walk must close exactly.", {(0, 3)}),
]


def diagram(i, x, y, w):
    """A small emblem for each finding."""
    cx, cy = x + w / 2, y + 62
    if i == 0:                  # one lap of a square helix: the top landing is the bottom landing
        s_, h = 46, 17

        def iso(x_, y_, z_):
            return cx + 20 + (x_ - y_) * 0.866, cy + 44 + (x_ + y_) * 0.5 - z_
        corners = [(-s_, s_), (s_, s_), (s_, -s_), (-s_, -s_), (-s_, s_)]
        pts = [iso(x_, y_, k * h) for k, (x_, y_) in enumerate(corners)]
        for k in range(4):
            svg.poly([pts[k], pts[k + 1]], w=mm(0.45), color=INK if k < 3 else RED)
            a_, b_ = pts[k], pts[k + 1]
            m_ = ((a_[0] + b_[0]) / 2, (a_[1] + b_[1]) / 2)
            ang = math.atan2(b_[1] - a_[1], b_[0] - a_[0])
            svg.poly([(m_[0] + 6 * math.cos(ang), m_[1] + 6 * math.sin(ang)),
                      (m_[0] + 6 * math.cos(ang + 2.6), m_[1] + 6 * math.sin(ang + 2.6)),
                      (m_[0] + 6 * math.cos(ang - 2.6), m_[1] + 6 * math.sin(ang - 2.6))],
                     w=0, fill=INK if k < 3 else RED, closed=True)
        svg.line(pts[0][0], pts[0][1], pts[4][0], pts[4][1], w=mm(0.3), color=RED, dash="4,3")
        for p_, lab in ((pts[0], "LEVEL 1"), (pts[4], "LEVEL 1")):
            svg.circle(*p_, 3.8, sw=0, fill=RED)
            svg.text(p_[0] - 10, p_[1] + 4, lab, size=pt(5.4), family="Copperplate", anchor="end", color=RED, spacing=1)
        for k, lab in ((1, "2"), (2, "3"), (3, "4")):
            svg.text(pts[k][0] + (9 if k != 3 else -9), pts[k][1] + 4, lab, size=pt(7), family=MATH,
                     anchor="start" if k != 3 else "end")
    elif i == 1:                # five right turns round a square
        s = 46
        corners = [(cx + s, cy + s), (cx - s, cy + s), (cx - s, cy - s), (cx + s, cy - s), (cx + s, cy + s), (cx - s, cy + s)]
        off = [0, 4, 8, 12, 16, 20]
        pts = []
        for k, (px, py) in enumerate(corners):
            o = off[k] * 0.55
            pts.append((px + (-o if px > cx else o), py + (-o if py > cy else o)))
        svg.poly(pts[:5], w=mm(0.35), color=INK)
        svg.poly(pts[4:], w=mm(0.45), color=RED)
        svg.circle(cx, cy, 4, sw=mm(0.3))
        for k in range(1, 6):
            px, py = pts[k] if k < 5 else pts[5]
            svg.text(px + (10 if px > cx else -16), py + (16 if py > cy else -6), str(k), size=pt(7), family=MATH,
                     color=RED if k == 5 else INK)
    else:                       # a hall a quarter inch too long
        L = 150
        svg.line(cx - L / 2, cy - 14, cx + L / 2, cy - 14, w=mm(0.45), color=INK)
        svg.line(cx - L / 2, cy + 14, cx + L / 2 + 10, cy + 14, w=mm(0.45), color=RED)
        for xx in (cx - L / 2,):
            svg.line(xx, cy - 24, xx, cy + 24, w=mm(0.25))
        svg.line(cx + L / 2, cy - 24, cx + L / 2, cy + 4, w=mm(0.25))
        svg.line(cx + L / 2 + 10, cy - 4, cx + L / 2 + 10, cy + 24, w=mm(0.25), color=RED)
        svg.text(cx, cy - 22, "ROOMS  38′-6″", size=pt(6), family="Copperplate", anchor="middle", spacing=1)
        svg.text(cx, cy + 36, "HALL  38′-6¼″", size=pt(6), family="Copperplate", anchor="middle", spacing=1, color=RED)


for i, (num, title, seam, desc, conclusion, hl) in enumerate(finds):
    x = X0 + i * (fw + gap)
    L = loops[seam]
    hol = L["holonomy"]
    M = Motion(hol["turns"], tuple(hol["t"])).matrix()
    svg.text(x + fw / 2, FY + 6, num, size=pt(20), family=DIDOT, anchor="middle", color=RED)
    caps(x + fw / 2, FY + 34, title, pt(8), family="Copperplate", spacing=3)
    yy = set_paragraph(svg, x, FY + 60, fw, desc, SERIF, pt(9.6), pt(12.6), italic=True, justify=False,
                       align="center")
    diagram(i, x, yy - 6, fw)
    yy += 150
    keys = [st[1] for st in L["loop"]]
    names = [k.replace("HALL", "H") for k in keys]
    lw = 0
    tx = x + fw / 2 - (len(names) * 34) / 2 - 18
    end = subscripted(tx, yy, "T", names, size=pt(10))
    svg.text(end + 2, yy, "=", size=pt(10.5), family=MATH)
    yy += 14
    mw, mh = matrix(x + fw / 2 - 92, yy, M, size=pt(9), highlight=hl)
    svg.text(x + fw / 2 - 92 + mw + 10, yy + mh / 2 + 7, "≠ I", size=pt(13), family=MATH, color=RED)
    yy += mh + 26
    walk = " · ".join(keys)
    svg.text(x + fw / 2, yy, f"walk: {walk}", size=pt(6.4), family=MONO, anchor="middle", color=GREEN)
    yy += 22
    set_paragraph(svg, x + 10, yy, fw - 20, "Carried once round, a frame of reference comes home changed: "
                  + conclusion, SERIF, pt(9), pt(11.8), justify=False, align="center")

y = FY + 440

# ============================================================================= proof
svg.line(X0, y, X1, y, w=mm(0.15), color=GREEN)
y += 34
proof1 = ("Were the property to exist, each room could be given a place in ordinary space, a position and a "
          "heading, so that every doorway met its partner exactly. A frame of reference carried through the "
          "doorways of any closed walk would then come home unchanged: the product of the walk’s "
          "transformations would be the identity. Each of the three walks above comes home changed. Hence "
          "no such placement exists.  ∎")
svg.text(X0, y, "PROOF.", size=pt(8.5), family="Copperplate", weight=700, spacing=2, color=GREEN)
y = set_paragraph(svg, X0, y, X1 - X0, proof1, SERIF, pt(10.5), pt(14.4), first_indent=72)
y += 6
proof2 = (f"The same conclusion was reached independently by the Z3 theorem prover, version {CERT['z3_version']}, "
          f"which reports the twenty-two doorway constraints unsatisfiable and names doorways "
          f"{', '.join(CERT['core'][:-1])} and {CERT['core'][-1]} as a minimal contradiction. Of the "
          f"{CERT['triples_tried']:,} ways of bricking up three doorways, exactly {len(CERT['fixes_three'])} "
          f"would allow the property to exist; no single doorway, and no pair, suffices. The solver’s proof "
          f"is printed in full around the border of this certificate.")
y = set_paragraph(svg, X0, y, X1 - X0, proof2, SERIF, pt(10.5), pt(14.4))

# ============================================================================= solver record
y += 14
bx0, bx1 = X0, X1 - 250
svg.rect(bx0, y, bx1 - bx0, 128, stroke=GREEN, sw=mm(0.3), fill=WHITE)
lines = [
    "$ python3 -m nonexistence.prove",
    f"rooms ........ {CERT['rooms']:<6} local inspections .. {CERT['local_checks']} / {CERT['local_checks']} passed",
    f"doorways ..... {CERT['doorways']:<6} existence .......... {CERT['verdict']}",
    "unsat core ... " + ", ".join(f"doorway {c}" for c in CERT["core"]),
    f"proof ........ {CERT['proof_lines']} lines, {CERT['proof_chars']:,} characters (see border)",
    f"sha-256 ...... {CERT['sha256']}",
    "$ python3 verify.py   # no solver, whole numbers only",
    "3 loop(s) fail to close. The building cannot exist in Euclidean space.",
]
for i, ln in enumerate(lines):
    svg.text(bx0 + 14, y + 20 + i * 14.4, ln, size=pt(6.6), family=MONO, color=INK if not ln.startswith("$") else GREEN)

# QR: the certificate in machine-readable form
qr_payload = (f"CERTIFICATE OF NONEXISTENCE|No.1 Holonomy Lane, Charlotte NC|sha256:{CERT['sha256']}|"
              + "|".join(f"{'.'.join(st[1] for st in L['loop'])}:turns={L['holonomy']['turns']},t={L['holonomy']['t']}"
                         for L in CERT["loops"])
              + f"|units=quarter-inch|z3 {CERT['z3_version']}:unsat")
q = qrcode.QRCode(border=0, error_correction=qrcode.constants.ERROR_CORRECT_M)
q.add_data(qr_payload)
q.make(fit=True)
mtx = q.get_matrix()
n = len(mtx)
qs = 128 / n
qx, qy = X1 - 128, y
for r in range(n):
    for c in range(n):
        if mtx[r][c]:
            svg.rect(qx + c * qs, qy + r * qs, qs + 0.15, qs + 0.15, sw=0, fill=INK)
svg.text(qx - 12, qy + 10, "SCAN TO", size=pt(5.2), family="Copperplate", anchor="end", color=GREEN, spacing=1)
svg.text(qx - 12, qy + 20, "READ THE", size=pt(5.2), family="Copperplate", anchor="end", color=GREEN, spacing=1)
svg.text(qx - 12, qy + 30, "HOLONOMIES", size=pt(5.2), family="Copperplate", anchor="end", color=GREEN, spacing=1)
y += 128

# ============================================================================= signatures, seal, stamp
y += 40
svg.text(CX, y, "Issued at Charlotte, North Carolina, this fifth day of November, two thousand and twenty-six.",
         size=pt(10.5), family=SERIF, italic=True, anchor="middle")
sy = y + 92


def signature(x, sig, line1, line2, font="Snell Roundhand", size=pt(30), color=PEN):
    if sig:
        svg.text(x, sy - 10, sig, size=size, family=font, anchor="middle", color=color)
    svg.line(x - 150, sy, x + 150, sy, w=mm(0.25))
    svg.text(x, sy + 18, line1, size=pt(7.2), family="Copperplate", anchor="middle", spacing=1.5)
    svg.text(x, sy + 32, line2, size=pt(6), family=SERIF, italic=True, anchor="middle", color="#55524c")


signature(X0 + 520, "unsat", "INSPECTOR OF EXISTENCE", f"the Z3 theorem prover, version {CERT['z3_version']}")
signature(X1 - 190, ARTIST or "", "ARCHITECT", ARTIST or "signed by hand")

# seal: a red foil starburst with ∄ at its centre
scx, scy = X0 + 112, sy - 36
pts = []
for i in range(144):
    a = 2 * math.pi * i / 144
    r = 104 if i % 2 == 0 else 96
    pts.append((scx + r * math.cos(a), scy + r * math.sin(a)))
svg.defs.append('<radialGradient id="foil" cx="40%" cy="35%" r="75%"><stop offset="0" stop-color="#d9553a"/>'
                '<stop offset="0.55" stop-color="#b3301c"/><stop offset="1" stop-color="#7f1d10"/></radialGradient>')
svg.poly(pts, w=0, fill="url(#foil)", closed=True)
svg.circle(scx, scy, 86, color="#f3d9c9", sw=mm(0.35))
svg.circle(scx, scy, 58, color="#f3d9c9", sw=mm(0.25))
ring = "BUREAU OF EUCLIDEAN INSPECTION ✦ DIVISION OF EXISTENCE ✦ "
cw = 2 * math.pi / len(ring)
for i, ch in enumerate(ring):
    a = -math.pi / 2 + i * cw
    px, py = scx + 72 * math.cos(a), scy + 72 * math.sin(a)
    svg.text(px, py + 4, ch, size=pt(8), family="Copperplate", weight=700, anchor="middle", color="#f6e3d6",
             rotate=math.degrees(a) + 90)
svg.text(scx, scy + 26, "∄", size=pt(58), family=MATH, anchor="middle", color="#f6e3d6")

# rubber stamp, struck at an angle, with a worn face
sx_, sy_ = X1 - 190, None
fid = svg.uid("ink")
# The stamp's ink is lifted by two kinds of noise: the paper's tooth (fine) and uneven pressure
# across the rubber (broad). Letter edges are nudged by a third noise so they spread like ink.
svg.defs.append(
    f'<filter id="{fid}" x="-0.1" y="-0.3" width="1.2" height="1.6" color-interpolation-filters="sRGB">'
    '<feTurbulence type="fractalNoise" baseFrequency="0.45" numOctaves="2" seed="5" result="e0"/>'
    '<feDisplacementMap in="SourceGraphic" in2="e0" scale="2.4" xChannelSelector="R" yChannelSelector="G" result="ragged"/>'
    '<feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="7" result="t0"/>'
    '<feColorMatrix in="t0" type="matrix" values="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 0 0 0 0 1" result="tooth"/>'
    '<feTurbulence type="fractalNoise" baseFrequency="0.011 0.02" numOctaves="3" seed="3" result="p0"/>'
    '<feColorMatrix in="p0" type="matrix" values="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 0 0 0 0 1" result="press"/>'
    '<feComposite in="tooth" in2="press" operator="arithmetic" k1="0" k2="0.5" k3="0.5" k4="0" result="v"/>'
    '<feColorMatrix in="v" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 -9 0 0 0 5.15" result="holes"/>'
    '<feComposite in="ragged" in2="holes" operator="in"/>'
    '</filter>')
sy_ = sy - 22
svg.open(transform=f"translate({sx_},{sy_}) rotate(-8)", opacity=0.9)
svg.open(filter=f"url(#{fid})")
svg.rect(-205, -62, 410, 124, stroke=RED, sw=mm(1.1))
svg.rect(-196, -53, 392, 106, stroke=RED, sw=mm(0.4))
svg.text(0, 4, "DOES NOT EXIST", size=pt(30), family="DIN Condensed", weight=700, anchor="middle", color=RED,
         spacing=3)
svg.text(0, 36, f"INSPECTED 05 NOV 2026 · No. {serial[:8]}", size=pt(8.5), family="DIN Condensed", weight=700,
         anchor="middle", color=RED, spacing=2)
svg.text(0, -32, "BUREAU OF EUCLIDEAN INSPECTION", size=pt(7.5), family="DIN Condensed", weight=700,
         anchor="middle", color=RED, spacing=2.5)
svg.close()
svg.close()

svg.text(X0, H - 232, f"No. {serial_fmt}", size=pt(9), family=MONO, weight=700, color=RED, spacing=1.5)
svg.text(X1, H - 232, "This certificate may be verified by anyone, without trust, by running verify.py.",
         size=pt(7.5), family=SERIF, italic=True, anchor="end", color=GREEN)


if __name__ == "__main__":
    out = ROOT / "out" / "plates"
    out.mkdir(parents=True, exist_ok=True)
    svg.save(out / "03_certificate.svg")
