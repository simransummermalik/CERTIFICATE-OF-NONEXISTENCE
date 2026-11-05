"""The finished images: no captions, no text, just the pictures.

    .venv/bin/python drawings/images.py

  01  The house, built anyway: ink drawing, 18 x 24 in at 300 dpi, on drafting paper
  02  The stair hall, looking down     (black-and-white photograph)
  03  The stair hall, looking up       (black-and-white photograph)
  04  The hall                         (black-and-white photograph)

Everything is written to submission/ as a full-resolution JPEG plus a 2400 px version for
screens, and to out/images/ as lossless PNG.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import finish as F  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "images"
SUBMIT = ROOT / "submission"
ICC = F.ICC.read_bytes() if F.ICC.exists() else None
TITLE = "Certificate_of_Nonexistence"

F.MONO.update({
    "vertigo": (0.20, 0.93, 1.22),
    "hero_a": (0.17, 0.95, 1.12),
    "hall": (0.22, 0.97, 1.30),
})


def save(im, stem, dpi):
    OUT.mkdir(parents=True, exist_ok=True)
    SUBMIT.mkdir(exist_ok=True)
    im.save(OUT / f"{stem}.png", dpi=(dpi, dpi), icc_profile=ICC)
    im.save(SUBMIT / f"{stem}.jpg", quality=94, subsampling=0, dpi=(dpi, dpi), icc_profile=ICC)
    web = im.copy()
    web.thumbnail((2400, 2400), Image.LANCZOS)
    web.save(SUBMIT / f"{stem}_web.jpg", quality=90, subsampling=0, icc_profile=ICC)
    print("wrote", stem, im.size, flush=True)


def place(ink, side=270, top=300, bottom=420):
    """Set the drawing on the sheet with margins, the bottom one deeper, as a mount is cut."""
    a = np.asarray(ink)
    ys, xs = np.nonzero(a < 245)
    box = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
    art = ink.crop(box)
    s = min(1.0, (F.W - 2 * side) / art.width, (F.H - top - bottom) / art.height)
    if s < 1.0:
        art = art.resize((round(art.width * s), round(art.height * s)), Image.LANCZOS)
    sheet = Image.new("L", (F.W, F.H), 255)
    x = (F.W - art.width) // 2
    y = top + (F.H - top - bottom - art.height) // 2
    sheet.paste(art, (x, y))
    print(f"drawing {art.size} at {x},{y} (scale {s:.3f})", flush=True)
    return sheet


def drawing():
    ink = Image.open(ROOT / "out/anyway/final_ink.png").convert("L")
    assert ink.size == (F.W, F.H), ink.size
    ink = place(ink)
    # ink sits into the paper a little: the faintest softening, as a pen line does
    ink = ink.filter(ImageFilter.GaussianBlur(0.45))
    a = np.asarray(ink).astype(np.float32) / 255.0
    sheet = F.paper(22, (0.972, 0.962, 0.938), mottle=0.0035, tooth=0.008)
    # the ink is a warm black, not a screen black
    inkc = np.array([0.075, 0.072, 0.070], np.float32)
    rgb = sheet * (inkc + (1 - inkc) * a[..., None])
    return Image.fromarray((np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8), "RGB")


def photo(shot, seed):
    src = Image.open(ROOT / f"out/renders/final_{shot}.png")
    a = F.photograph(ROOT / f"out/renders/final_{shot}.png", src.size, seed, shot)
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8), "RGB")


def main():
    which = sys.argv[1:] or ["1", "2", "3", "4"]
    if "1" in which:
        save(drawing(), f"01_{TITLE}_The_House_Built_Anyway", 300)
    if "2" in which:
        save(photo("vertigo", 201), f"02_{TITLE}_Stair_Hall_Looking_Down", 300)
    if "3" in which:
        save(photo("hero_a", 202), f"03_{TITLE}_Stair_Hall_Looking_Up", 300)
    if "4" in which:
        save(photo("hall", 203), f"04_{TITLE}_The_Hall", 300)


if __name__ == "__main__":
    main()
