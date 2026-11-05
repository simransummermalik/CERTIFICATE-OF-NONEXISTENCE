"""Plate I — THE PROPERTY.  A luxury listing for a house that cannot be built.

The photographs are path-traced in Blender from the same room dimensions the
solver checks. This file lays out the page; finish.py places the photographs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from drawings.svg import SVG, pt, mm  # noqa: E402
from drawings.typeset import set_paragraph, width  # noqa: E402

CERT = json.loads((ROOT / "out/proof/certificate.json").read_text())
INK = "#1c1b19"
GREY = "#7a766e"
RULE = "#b9b4aa"
RED = "#b8321f"
SERIF = "Baskerville"
DIDOT = "Didot"
SMALL = "Copperplate"

svg = SVG(18, 24)
W, H = svg.W, svg.H
L, R = 100.0, 1700.0
SLOTS = {}


def photo(key, x, y, w, h, n, caption):
    SLOTS[key] = (x, y, w, h)
    svg.rect(x, y, w, h, stroke="none", sw=0, fill="#d8d4cc")
    svg.text(x, y + h + 26, f"{n:02d} / 04", size=pt(7), family=SMALL, color=GREY, spacing=1.5)
    svg.text(x + 74, y + h + 26, caption, size=pt(9.5), family=SERIF, weight=400, italic=True, color=INK)


# ---------------------------------------------------------------------------- masthead
svg.text(L, 132, "HILBERT & CO.", size=pt(22), family=DIDOT, spacing=9, color=INK)
svg.text(L, 160, "FINE PROPERTIES  ·  ROOMS WITHOUT END  ·  EST. 1924", size=pt(6.5), family=SMALL,
         spacing=2.2, color=GREY)
svg.text(R, 132, "EXCLUSIVE LISTING", size=pt(9), family=SMALL, spacing=3, anchor="end", color=INK)
serial = CERT["sha256"][:8].upper()
svg.text(R, 160, f"LISTING No. {serial[:4]}-{serial[4:]}", size=pt(6.5), family=SMALL, spacing=2.2, anchor="end",
         color=GREY)
svg.line(L, 188, R, 188, w=mm(0.5), color=INK)
svg.line(L, 194, R, 194, w=mm(0.12), color=INK)

# ---------------------------------------------------------------------------- hero
HX, HY, HW = L, 236, 1040
HH = HW * 4 / 3
photo("vertigo", HX, HY, HW, HH, 1, "The stair hall, looking down from Level 1")

# ---------------------------------------------------------------------------- right column
cx = HX + HW + 56
cw = R - cx
y = 300
svg.text(cx, y, "FOR SALE", size=pt(7.5), family=SMALL, spacing=3, color=GREY)
y += 120
svg.text(cx - 6, y, "No. 1", size=pt(92), family=DIDOT, color=INK)
y += 70
svg.text(cx, y, "Holonomy Lane", size=pt(36), family=DIDOT, italic=True, color=INK)
y += 40
svg.text(cx, y, "CHARLOTTE  ·  NORTH CAROLINA", size=pt(7), family=SMALL, spacing=2.5, color=GREY)
y += 46
svg.line(cx, y, R, y, w=mm(0.25), color=RULE)
y += 44
svg.text(cx, y, "Price upon request", size=pt(16), family=SERIF, weight=400, italic=True, color=INK)
y += 36
svg.line(cx, y, R, y, w=mm(0.25), color=RULE)

facts = [("BEDROOMS", "2"), ("BATH", "1"), ("STOREYS", "4"), ("ROOMS", "18"),
         ("INTERIOR", "3,974 sq ft"), ("YEAR BUILT", "—")]
y += 40
for i, (k, v) in enumerate(facts):
    col, row = i % 2, i // 2
    x = cx + col * (cw / 2)
    yy = y + row * 64
    svg.text(x, yy, k, size=pt(6.2), family=SMALL, spacing=2, color=GREY)
    svg.text(x, yy + 30, v, size=pt(17), family=DIDOT, color=INK)
y += 3 * 64 + 10
svg.line(cx, y, R, y, w=mm(0.25), color=RULE)
y += 46

copy = [
    "A house of rare and exacting proportions. Every room has been drawn to the quarter inch and "
    "inspected to code, and not one has ever been found wanting.",
    "At its heart, a stair hall of board-formed concrete climbs four full storeys through falling daylight "
    "and returns you, unhurried, to the landing where you began. A cloister of five galleries turns about a "
    "court of raked gravel, where a single stone keeps more than its share of the horizon. The long hall, "
    "oak-floored and skylit, is generous by exactly one quarter of an inch.",
]
for para in copy:
    y = set_paragraph(svg, cx, y, cw, para, SERIF, pt(11.2), pt(15.6), justify=True)
    y += 14

y += 10
svg.text(cx, y, "HIGHLIGHTS", size=pt(6.5), family=SMALL, spacing=2.5, color=GREY)
y += 30
for h in ["Four-storey stair hall, open above and below", "Cloister of five corners about a gravel court",
          "Skylit hall in white oak, 38 ft 6¼ in", "Library with west light", "Certificate of inspection on file"]:
    svg.circle(cx + 4, y - 5, 2.4, sw=0, fill=INK)
    svg.text(cx + 18, y, h, size=pt(10.4), family=SERIF, weight=400, color=INK)
    y += 25

# viewings: anchored to the foot of the hero so the column ends where the photograph does
vy = HY + HH - 150
svg.line(cx, vy, R, vy, w=mm(0.25), color=RULE)
svg.text(cx, vy + 40, "VIEWINGS", size=pt(6.5), family=SMALL, spacing=2.5, color=GREY)
set_paragraph(svg, cx, vy + 76, cw,
              "By appointment only. Allow forty minutes for the house, and longer for the stair. "
              "Buyers are advised to verify existence before closing.",
              SERIF, pt(11.2), pt(15.6), italic=True, justify=False)

# ---------------------------------------------------------------------------- the three photographs
by = HY + HH + 100
gap = 44
pw = (R - L - 2 * gap) / 3
ph = pw * 2 / 3
photo("landing_view", L, by, pw, ph, 2, "Landing, Level 1")
photo("hall", L + pw + gap, by, pw, ph, 3, "The long hall, looking east")
photo("tape", L + 2 * (pw + gap), by, pw, ph, 4, "The hall, measured")

# ---------------------------------------------------------------------------- footer
fy = by + ph + 124
svg.line(L, fy, R, fy, w=mm(0.12), color=INK)
svg.line(L, fy + 6, R, fy + 6, w=mm(0.5), color=INK)
svg.text(L, fy + 50, "HILBERT & CO.", size=pt(10), family=DIDOT, spacing=5, color=INK)
svg.text(L, fy + 74, "Fine Properties  ·  Charlotte, North Carolina", size=pt(8.5), family=SERIF, weight=400, italic=True,
         color=GREY)
svg.text(L, fy + 96, "A hotel of infinitely many rooms, always room for one more.", size=pt(8.5), family=SERIF,
         weight=400, italic=True, color=GREY)
disc = ("All measurements are exact to the quarter inch. Square footage includes one gallery counted twice. "
        "Photographs are faithful renderings of each room as it is locally. "
        "Information deemed reliable but not guaranteed to exist.")
set_paragraph(svg, 900, fy + 46, R - 900, disc, SERIF, pt(8.2), pt(11.4), color=GREY, justify=True)

if __name__ == "__main__":
    out = ROOT / "out" / "plates"
    out.mkdir(parents=True, exist_ok=True)
    svg.save(out / "01_property.svg")
    (out / "01_property_slots.json").write_text(json.dumps(SLOTS, indent=1))
    print(SLOTS)
