"""Measure text with the real font files so lines can be set and justified by hand."""

from functools import lru_cache

from PIL import ImageFont

SUP = "/System/Library/Fonts/Supplemental/"
SYS = "/System/Library/Fonts/"

FILES = {
    ("Baskerville", 400, False): (SUP + "Baskerville.ttc", 0),
    ("Baskerville", 700, False): (SUP + "Baskerville.ttc", 1),
    ("Baskerville", 400, True): (SUP + "Baskerville.ttc", 2),
    ("Baskerville", 600, False): (SUP + "Baskerville.ttc", 4),
    ("Baskerville", 600, True): (SUP + "Baskerville.ttc", 5),
    ("Didot", 400, False): (SUP + "Didot.ttc", 0),
    ("Didot", 400, True): (SUP + "Didot.ttc", 1),
    ("Didot", 700, False): (SUP + "Didot.ttc", 2),
    ("STIX Two Text", 400, False): (SUP + "STIXTwoText.ttf", 0),
    ("STIX Two Text", 400, True): (SUP + "STIXTwoText-Italic.ttf", 0),
    ("Menlo", 400, False): (SYS + "Menlo.ttc", 0),
    ("Menlo", 700, False): (SYS + "Menlo.ttc", 1),
    ("Copperplate", 400, False): (SUP + "Copperplate.ttc", 0),
    ("Copperplate", 300, False): (SUP + "Copperplate.ttc", 1),
    ("Copperplate", 700, False): (SUP + "Copperplate.ttc", 2),
    ("Snell Roundhand", 400, False): (SUP + "SnellRoundhand.ttc", 0),
    ("DIN Condensed", 700, False): (SUP + "DIN Condensed Bold.ttf", 0),
    ("Avenir Next Condensed", 500, False): (SYS + "Avenir Next Condensed.ttc", 5),
    ("Avenir Next Condensed", 600, False): (SYS + "Avenir Next Condensed.ttc", 2),
}


@lru_cache(maxsize=None)
def _font(family, weight, italic):
    path, idx = FILES[(family, weight, italic)]
    return ImageFont.truetype(path, 200, index=idx)


def width(text, family, size, weight=400, italic=False, spacing=0.0):
    f = _font(family, weight, italic)
    return f.getlength(text) * size / 200.0 + spacing * max(0, len(text) - 1)


def wrap(text, maxw, family, size, weight=400, italic=False):
    words = text.split()
    lines, cur = [], []
    for w in words:
        trial = " ".join(cur + [w])
        if cur and width(trial, family, size, weight, italic) > maxw:
            lines.append(cur)
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(cur)
    return lines


def set_paragraph(svg, x, y, maxw, text, family, size, lead, weight=400, italic=False, color="#1b1a17",
                  justify=True, align="left", first_indent=0.0):
    """Typeset a paragraph. Returns the y below the last line."""
    lines = wrap(text, maxw - first_indent, family, size, weight, italic)
    # rewrap after the first line with full width
    if first_indent and len(lines) > 1:
        rest = " ".join(" ".join(l) for l in lines[1:])
        lines = lines[:1] + wrap(rest, maxw, family, size, weight, italic)
    for i, words in enumerate(lines):
        x0 = x + (first_indent if i == 0 else 0)
        w_avail = maxw - (first_indent if i == 0 else 0)
        last = i == len(lines) - 1
        if justify and not last and len(words) > 1:
            ws = [width(w, family, size, weight, italic) for w in words]
            gap = (w_avail - sum(ws)) / (len(words) - 1)
            cx = x0
            for w, wl in zip(words, ws):
                svg.text(cx, y, w, size=size, family=family, weight=weight, italic=italic, color=color)
                cx += wl + gap
        else:
            line = " ".join(words)
            if align == "center":
                svg.text(x + maxw / 2, y, line, size=size, family=family, weight=weight, italic=italic,
                         color=color, anchor="middle")
            else:
                svg.text(x0, y, line, size=size, family=family, weight=weight, italic=italic, color=color)
        y += lead
    return y
