"""Finishing: rasterize the three plates at 300 dpi, set the photographs, and print them onto paper.

    python drawings/finish.py            # all three plates
    python drawings/finish.py 1          # just Plate I

Each sheet is 18 x 24 in. Ink is multiplied onto a sheet of paper made from seeded noise,
so the result is the same every time it is built. The certificate gets the red and blue
security fibres of banknote paper; the plan gets plain drafting bond; the listing gets bright
coated stock. Photographs get a fine grain, as if printed rather than displayed.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps

Image.MAX_IMAGE_PIXELS = None

ROOT = Path(__file__).resolve().parent.parent
PLATES = ROOT / "out" / "plates"
RENDERS = ROOT / "out" / "renders"
SUBMIT = ROOT / "submission"
DPI = 300
W, H = 18 * DPI, 24 * DPI
PX = DPI / 100.0                       # svg user units are 1/100 in
ICC = Path("/System/Library/ColorSync/Profiles/sRGB Profile.icc")
TITLE = "Certificate_of_Nonexistence"


# ----------------------------------------------------------------------------- paper
def gaussian_filter(a, sigma):
    """Small separable Gaussian blur (enough for grain; keeps the build to numpy and Pillow)."""
    r = max(1, int(3 * sigma + 0.5))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2).astype(np.float32)
    k /= k.sum()
    out = np.zeros_like(a)
    for i, w in enumerate(k):
        out += w * np.roll(a, i - r, axis=0)
    a, out = out, np.zeros_like(a)
    for i, w in enumerate(k):
        out += w * np.roll(a, i - r, axis=1)
    return out


def field(rng, scale, shape=(H, W)):
    """Smooth noise with features about `scale` pixels across, unit variance."""
    h, w = shape
    small = rng.standard_normal((h // scale + 3, w // scale + 3)).astype(np.float32)
    im = Image.fromarray(small, mode="F").resize((w + 3 * scale, h + 3 * scale), Image.BICUBIC)
    a = np.asarray(im)[scale:scale + h, scale:scale + w]
    return (a - a.mean()) / (a.std() + 1e-6)


def paper(seed, base, mottle, tooth):
    """An RGB float32 sheet in 0..1: base colour, soft cloudy mottling, fine tooth."""
    rng = np.random.default_rng(seed)
    lum = 0.62 * field(rng, 420) + 0.30 * field(rng, 110) + 0.08 * field(rng, 28)
    lum *= mottle
    t = gaussian_filter(rng.standard_normal((H, W)).astype(np.float32), 0.8)
    t /= t.std() + 1e-6
    lum += tooth * t
    lum += 1.0
    sheet = np.empty((H, W, 3), np.float32)
    for c in range(3):
        sheet[..., c] = lum * base[c]
    return sheet


def fibres(sheet, seed, n_security, n_pale):
    """Embedded fibres: a few coloured security threads and many pale paper fibres."""
    rng = np.random.default_rng(seed)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    def curl(length, width, rgba):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        a = rng.uniform(0, np.pi)
        bend = rng.normal(0, 0.9)
        pts = []
        for i in range(9):
            s = i / 8
            ang = a + bend * (s - 0.5)
            pts.append((x, y))
            x += np.cos(ang) * length / 8
            y += np.sin(ang) * length / 8
        d.line(pts, fill=rgba, width=width, joint="curve")

    for _ in range(n_pale):
        g = int(rng.uniform(200, 240))
        curl(rng.uniform(25, 90), 1, (g, g - 6, g - 18, int(rng.uniform(18, 45))))
    for _ in range(n_security):
        red = rng.random() < 0.55
        rgba = (178, 44, 38, int(rng.uniform(70, 140))) if red else (38, 70, 150, int(rng.uniform(70, 140)))
        curl(rng.uniform(28, 70), int(rng.choice([1, 2])), rgba)

    f = np.asarray(layer).astype(np.float32) / 255.0
    alpha = f[..., 3:4]
    sheet *= 1.0 - alpha
    sheet += alpha * f[..., :3]
    return sheet


# ----------------------------------------------------------------------------- ink
def rasterize(svg_path):
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "r.png"
        subprocess.run(["rsvg-convert", "-w", str(W), "-h", str(H), "-b", "white", str(svg_path), "-o", str(out)],
                       check=True)
        return Image.open(out).convert("RGB")


def best_render(shot):
    final = RENDERS / f"final_{shot}.png"
    if final.exists():
        return final, True
    tests = sorted(RENDERS.glob(f"t*_{shot}.png"), key=lambda p: p.stat().st_mtime)
    return tests[-1], False


# A listing photographer lifts the midtones of a dim interior; black and white stay put.
LIFT = {"landing_view": 0.80, "vertigo": 0.94, "tape": 0.96}


def photograph(path, size, seed, lift=1.0):
    """Fit a render to its slot, lift its midtones, and give it a fine luminance-weighted grain."""
    im = Image.open(path).convert("RGB")
    im = ImageOps.fit(im, size, Image.LANCZOS, centering=(0.5, 0.5))
    a = np.asarray(im).astype(np.float32) / 255.0
    a **= lift
    rng = np.random.default_rng(seed)
    g = gaussian_filter(rng.standard_normal(a.shape[:2]).astype(np.float32), 0.55)
    g /= g.std() + 1e-6
    lum = a.mean(axis=2, keepdims=True)
    a += (g[..., None] * 0.012) * (0.35 + 0.65 * np.sqrt(np.clip(lum, 0, 1)))
    return np.clip(a, 0, 1)


def print_on(ink_rgb, sheet):
    ink = np.asarray(ink_rgb).astype(np.float32) / 255.0
    sheet *= ink
    return Image.fromarray((np.clip(sheet, 0, 1) * 255 + 0.5).astype(np.uint8), "RGB")


# ----------------------------------------------------------------------------- plates
def plate_property():
    ink = rasterize(PLATES / "01_property.svg")
    slots = json.loads((PLATES / "01_property_slots.json").read_text())
    arr = np.asarray(ink).astype(np.float32) / 255.0
    used = {}
    for i, (shot, (x, y, w, h)) in enumerate(slots.items()):
        x0, y0 = round(x * PX), round(y * PX)
        x1, y1 = round((x + w) * PX), round((y + h) * PX)
        path, final = best_render(shot)
        used[shot] = (path.name, final)
        arr[y0:y1, x0:x1] = photograph(path, (x1 - x0, y1 - y0), 100 + i, LIFT.get(shot, 1.0))
    ink = Image.fromarray((arr * 255 + 0.5).astype(np.uint8), "RGB")
    sheet = paper(11, (0.990, 0.986, 0.978), mottle=0.0035, tooth=0.0045)
    return print_on(ink, sheet), used


def plate_plan():
    ink = rasterize(PLATES / "02_floor_plan.svg")
    sheet = paper(22, (0.975, 0.966, 0.944), mottle=0.009, tooth=0.011)
    return print_on(ink, sheet), {}


def plate_certificate():
    ink = rasterize(PLATES / "03_certificate.svg")
    sheet = paper(33, (0.968, 0.950, 0.905), mottle=0.013, tooth=0.013)
    sheet = fibres(sheet, 34, n_security=520, n_pale=9000)
    return print_on(ink, sheet), {}


PLATE = {
    1: ("I_The_Property", plate_property),
    2: ("II_The_Floor_Plan", plate_plan),
    3: ("III_The_Certificate", plate_certificate),
}


def save(im, n, part):
    icc = ICC.read_bytes() if ICC.exists() else None
    SUBMIT.mkdir(exist_ok=True)
    stem = f"{n:02d}_{TITLE}_{part}"
    im.save(PLATES / f"{stem}_300dpi.png", dpi=(DPI, DPI), icc_profile=icc, optimize=False)
    im.save(SUBMIT / f"{stem}_18x24in_300dpi.jpg", quality=93, subsampling=0, dpi=(DPI, DPI), icc_profile=icc)
    web = im.resize((1800, 2400), Image.LANCZOS)
    web.save(SUBMIT / f"{stem}_web.jpg", quality=90, subsampling=0, dpi=(100, 100), icc_profile=icc)
    return web


def overview(webs):
    """The three plates side by side, as they would hang."""
    gap, pad = 120, 160
    w = 3 * 1800 + 2 * gap + 2 * pad
    h = 2400 + 2 * pad
    sheet = Image.new("RGB", (w, h), (233, 231, 227))
    for i, im in enumerate(webs):
        x = pad + i * (1800 + gap)
        shadow = Image.new("RGB", (1800, 2400), (205, 202, 196))
        sheet.paste(shadow, (x + 6, pad + 8))
        sheet.paste(im, (x, pad))
    sheet = sheet.resize((w // 2, h // 2), Image.LANCZOS)
    icc = ICC.read_bytes() if ICC.exists() else None
    sheet.save(SUBMIT / f"00_{TITLE}_triptych_overview.jpg", quality=90, icc_profile=icc)


def main():
    which = [int(a) for a in sys.argv[1:]] or [1, 2, 3]
    webs = {}
    for n in which:
        part, fn = PLATE[n]
        im, used = fn()
        webs[n] = save(im, n, part)
        note = "" if not used else "  photos: " + ", ".join(
            f"{k}={'final' if f else 'TEST ' + p}" for k, (p, f) in used.items())
        print(f"plate {n} done{note}", flush=True)
    if len(webs) == 3:
        overview([webs[1], webs[2], webs[3]])
        print("overview done")


if __name__ == "__main__":
    main()
