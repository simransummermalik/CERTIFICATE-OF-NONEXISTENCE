"""Ink a full-size drawing in strips, so a 5400 x 7200 sheet fits in memory.

    .venv/bin/python drawings/anyway_ink_strips.py out/anyway/final [rows_per_strip]

Same drawing as anyway_ink.ink(); each strip is inked with a margin of overlap and trimmed.
"""

import json
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, __import__("os").path.dirname(__file__))
import anyway_ink as A  # noqa: E402

Image.MAX_IMAGE_PIXELS = None


def main(prefix, rows=1200):
    meta = json.load(open(f"{prefix}_meta.json"))
    ss = meta.get("ss", 1)
    names = ["nx", "ny", "nz", "plane", "wx", "wy", "wz", "depth", "id", "light"]
    full = {k: np.asarray(Image.open(f"{prefix}_{k}.png")) for k in names}
    H, W = full["depth"].shape
    # global depth range, from a sample of the whole sheet
    D = full["depth"][::7, ::7].astype(np.float32) / 65535
    alpha = D > 0.01
    dd = (D - 0.02) / 0.98
    d0, d1 = meta["depth"]
    inv = 1 / d1 + dd * (1 / d0 - 1 / d1)
    dist = 1 / np.maximum(inv, 1e-6) if meta.get("inverse") else d0 + dd * (d1 - d0)
    rng = (float(np.percentile(dist[alpha], 1)), float(np.percentile(dist[alpha], 99.5)))
    pad = 8 * ss
    rows = rows - rows % ss
    out = Image.new("L", (W // ss, H // ss), 255)
    for y0 in range(0, H, rows):
        a, b = max(0, y0 - pad), min(H, y0 + rows + pad)
        tmp = f"{prefix}__strip"
        for k in names:
            Image.fromarray(full[k][a:b]).save(f"{tmp}_{k}.png")
        json.dump(dict(meta, depth_range=rng, row0=a, width=W), open(f"{tmp}_meta.json", "w"))
        im = A.ink(tmp, out=f"{tmp}_ink.png", ss=1)
        arr = np.asarray(im)[(y0 - a):(y0 - a) + min(rows, H - y0)]
        strip = Image.fromarray(arr).resize((W // ss, arr.shape[0] // ss), Image.BOX)
        out.paste(strip, (0, y0 // ss))
        print(f"rows {y0}..{min(H, y0 + rows)}", flush=True)
    out.save(f"{prefix}_ink.png")
    for k in names + ["ink"]:
        __import__("os").remove(f"{prefix}__strip_{k}.png")
    __import__("os").remove(f"{prefix}__strip_meta.json")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 1200)
