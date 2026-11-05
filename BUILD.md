# Building No. 1 Holonomy Lane

## The plates

| Plate | File (in `submission/`) |
|---|---|
| I · The Property | `01_Certificate_of_Nonexistence_I_The_Property_*.jpg` |
| II · The Floor Plan | `02_Certificate_of_Nonexistence_II_The_Floor_Plan_*.jpg` |
| III · The Certificate | `03_Certificate_of_Nonexistence_III_The_Certificate_*.jpg` |
| All three, side by side | `00_Certificate_of_Nonexistence_triptych_overview.jpg` |

Each plate comes in two sizes. `*_18x24in_300dpi.jpg` is for print. `*_web.jpg` is 1800 × 2400 for screens. Lossless PNG masters are in `out/plates/`.

## Rebuild everything

The Python dependencies are in `.venv`: z3-solver, numpy, Pillow and qrcode. You also need Blender 5.x and `rsvg-convert` (`brew install librsvg`).

```
.venv/bin/python -m nonexistence.prove        # the proof, ~3 min  → out/proof/
.venv/bin/python render/tape.py               # tape-measure texture → out/textures/
./render/batch.sh final "vertigo 4000 256 0.75 50" "landing_view 2400 256 1.5 12" \
                        "hall 2400 256 1.5 1" "tape 2400 256 1.5 1"   # ~45 min → out/renders/
.venv/bin/python drawings/listing.py          # Plate I layout
.venv/bin/python drawings/plan.py             # Plate II
.venv/bin/python drawings/certificate.py      # Plate III
.venv/bin/python drawings/finish.py           # 300 dpi, paper, photographs → out/plates/, submission/
python3 verify.py                             # independent check, standard library only
```

Every step is deterministic: the same inputs give the same images.

## The artist's name

Put a name in `ARTIST.txt` to fill the DRAWN field on the plan and the ARCHITECT line on the certificate. Then rerun `plan.py`, `certificate.py` and `finish.py`. With the file absent or empty, the plan reads "THE ARTIST" and the architect's line stays blank.

## Where things are

| Path | What it is |
|---|---|
| `nonexistence/geometry.py` | Exact rigid motions in quarter-inch units and quarter turns |
| `nonexistence/building.py` | Rooms, doors, stairs, gluings and the IRC inspections |
| `nonexistence/holonomy_lane.py` | The house itself |
| `nonexistence/prove.py` | Layout, loop holonomies, Z3 encoding, unsat core, minimal fixes |
| `verify.py` | Standalone checker: hash and loop products in whole numbers |
| `render/scene.py` | Blender scenes. The stair hall is instanced lap after lap, so the well has no bottom. |
| `render/tape.py` | The tape-measure blade texture |
| `drawings/svg.py`, `typeset.py` | SVG primitives, drafting conventions, and text set with real font metrics |
| `drawings/listing.py`, `plan.py`, `certificate.py` | The three plates |
| `drawings/finish.py` | Rasterizing, paper, security fibres, photo grain and export |
