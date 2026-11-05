"""A very small SVG writer. Units are hundredths of an inch."""

from __future__ import annotations

import math
from html import escape

U = 100.0                     # units per inch


def pt(n: float) -> float:    # typographic points -> units
    return n * U / 72.0


def mm(n: float) -> float:    # pen widths
    return n / 25.4 * U


INK = "#17181b"
RED = "#c23b22"
GREY = "#7d7a74"
PAPER = "#f5f2ea"


def _f(v):
    if isinstance(v, float):
        s = f"{v:.2f}"
        return s.rstrip("0").rstrip(".") if "." in s else s
    return str(v)


def attrs(**kw):
    out = []
    for k, v in kw.items():
        if v is None or v is False:
            continue
        k = k.rstrip("_").replace("_", "-")
        out.append(f'{k}="{_f(v) if not isinstance(v, str) else escape(v, quote=True)}"')
    return " ".join(out)


class SVG:
    def __init__(self, w_in: float, h_in: float):
        self.W, self.H = w_in * U, h_in * U
        self.parts: list[str] = []
        self.defs: list[str] = []
        self._id = 0

    def uid(self, p="id"):
        self._id += 1
        return f"{p}{self._id}"

    def raw(self, s: str):
        self.parts.append(s)

    def open(self, **kw):
        self.parts.append(f"<g {attrs(**kw)}>")

    def close(self):
        self.parts.append("</g>")

    # ------------------------------------------------------------------ primitives
    def line(self, x1, y1, x2, y2, w=mm(0.25), color=INK, dash=None, cap="butt", opacity=None):
        self.parts.append(f"<line {attrs(x1=x1, y1=y1, x2=x2, y2=y2, stroke=color, stroke_width=w, stroke_dasharray=dash, stroke_linecap=cap, opacity=opacity)}/>")

    def poly(self, pts, w=mm(0.25), color=INK, fill="none", closed=False, dash=None, join="miter", opacity=None, fill_opacity=None, cap="butt", clip=None):
        d = " ".join(f"{_f(float(x))},{_f(float(y))}" for x, y in pts)
        tag = "polygon" if closed else "polyline"
        self.parts.append(f"<{tag} {attrs(points=d, stroke=color if w else 'none', stroke_width=w or None, fill=fill, stroke_dasharray=dash, stroke_linejoin=join, opacity=opacity, fill_opacity=fill_opacity, stroke_linecap=cap, clip_path=clip)}/>")

    def rect(self, x, y, w, h, stroke=INK, sw=mm(0.25), fill="none", dash=None, opacity=None, rx=None):
        x, w = (x, w) if w >= 0 else (x + w, -w)
        y, h = (y, h) if h >= 0 else (y + h, -h)
        self.parts.append(f"<rect {attrs(x=x, y=y, width=w, height=h, stroke=stroke if sw else 'none', stroke_width=sw or None, fill=fill, stroke_dasharray=dash, opacity=opacity, rx=rx)}/>")

    def circle(self, cx, cy, r, stroke=INK, sw=mm(0.25), fill="none", dash=None, opacity=None, color=None):
        stroke = color or stroke
        self.parts.append(f"<circle {attrs(cx=cx, cy=cy, r=r, stroke=stroke if sw else 'none', stroke_width=sw or None, fill=fill, stroke_dasharray=dash, opacity=opacity)}/>")

    def path(self, d, stroke=INK, sw=mm(0.25), fill="none", dash=None, opacity=None, join="round", cap="butt", fill_rule=None, clip=None):
        self.parts.append(f"<path {attrs(d=d, stroke=stroke if sw else 'none', stroke_width=sw or None, fill=fill, stroke_dasharray=dash, opacity=opacity, stroke_linejoin=join, stroke_linecap=cap, fill_rule=fill_rule, clip_path=clip)}/>")

    def text(self, x, y, s, size=pt(7), family="Avenir Next Condensed", weight=500, anchor="start",
             color=INK, spacing=None, rotate=None, italic=False, opacity=None, baseline=None):
        tr = f"rotate({_f(rotate)} {_f(x)} {_f(y)})" if rotate else None
        self.parts.append(
            f"<text {attrs(x=x, y=y, font_family=family, font_size=size, font_weight=weight, text_anchor=anchor, fill=color, letter_spacing=spacing, transform=tr, font_style='italic' if italic else None, opacity=opacity, dominant_baseline=baseline)}>{escape(s)}</text>")

    def clip_rect(self, x, y, w, h):
        cid = self.uid("clip")
        self.defs.append(f'<clipPath id="{cid}"><rect x="{_f(x)}" y="{_f(y)}" width="{_f(w)}" height="{_f(h)}"/></clipPath>')
        return f"url(#{cid})"

    def clip_poly(self, pts):
        cid = self.uid("clip")
        d = " ".join(f"{_f(float(x))},{_f(float(y))}" for x, y in pts)
        self.defs.append(f'<clipPath id="{cid}"><polygon points="{d}"/></clipPath>')
        return f"url(#{cid})"

    def save(self, path, background=None):
        bg = f'<rect width="100%" height="100%" fill="{background}"/>' if background else ""
        doc = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.W / U}in" height="{self.H / U}in" '
               f'viewBox="0 0 {_f(self.W)} {_f(self.H)}">\n<defs>{"".join(self.defs)}</defs>\n{bg}\n'
               + "\n".join(self.parts) + "\n</svg>\n")
        with open(path, "w") as f:
            f.write(doc)


# ---------------------------------------------------------------------- drafting helpers
def cloud(svg: SVG, x0, y0, x1, y1, r=12, color=RED, w=mm(0.35)):
    """Revision cloud around a rectangle."""
    pts = []
    perim = [(x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)]
    d = ""
    for (ax, ay, bx, by) in perim:
        L = math.hypot(bx - ax, by - ay)
        n = max(1, int(L / (2 * r)))
        for i in range(n):
            sx, sy = ax + (bx - ax) * i / n, ay + (by - ay) * i / n
            ex, ey = ax + (bx - ax) * (i + 1) / n, ay + (by - ay) * (i + 1) / n
            rr = math.hypot(ex - sx, ey - sy) / 2 * 1.08
            if not d:
                d = f"M{_f(sx)},{_f(sy)}"
            d += f" A{_f(rr)},{_f(rr)} 0 0 1 {_f(ex)},{_f(ey)}"
    svg.path(d + " Z", stroke=color, sw=w)


def arrowhead(svg: SVG, x, y, ang, size=10, color=INK, open_=False):
    a1, a2 = ang + math.radians(160), ang - math.radians(160)
    pts = [(x, y), (x + size * math.cos(a1), y + size * math.sin(a1)),
           (x + size * math.cos(a2), y + size * math.sin(a2))]
    svg.poly(pts, w=0 if not open_ else mm(0.25), color=color, fill=color if not open_ else "none", closed=not open_)


def tick(svg: SVG, x, y, size=5, w=mm(0.35), color=INK):
    svg.line(x - size, y + size, x + size, y - size, w=w, color=color)


def dim(svg: SVG, x1, y1, x2, y2, label, off=0.0, color=INK, size=pt(5.6), w=mm(0.13), ext=True, above=True,
        family="Avenir Next Condensed", weight=500):
    """Linear dimension between two points (horizontal or vertical), offset perpendicular by `off`."""
    if abs(y1 - y2) < 1e-6:   # horizontal
        y = y1 + off
        if ext:
            svg.line(x1, y1 + (3 if off > 0 else -3), x1, y + (4 if off > 0 else -4), w=w, color=color)
            svg.line(x2, y2 + (3 if off > 0 else -3), x2, y + (4 if off > 0 else -4), w=w, color=color)
        svg.line(x1 - 4, y, x2 + 4, y, w=w, color=color)
        tick(svg, x1, y, color=color)
        tick(svg, x2, y, color=color)
        svg.text((x1 + x2) / 2, y - 2.5 if above else y + size + 1, label, size=size, anchor="middle", color=color,
                 family=family, weight=weight)
    else:                      # vertical
        x = x1 + off
        if ext:
            svg.line(x1 + (3 if off > 0 else -3), y1, x + (4 if off > 0 else -4), y1, w=w, color=color)
            svg.line(x2 + (3 if off > 0 else -3), y2, x + (4 if off > 0 else -4), y2, w=w, color=color)
        svg.line(x, y1 - 4, x, y2 + 4, w=w, color=color)
        tick(svg, x, y1, color=color)
        tick(svg, x, y2, color=color)
        svg.text(x - 2.5, (y1 + y2) / 2, label, size=size, anchor="middle", color=color, rotate=-90,
                 family=family, weight=weight)
