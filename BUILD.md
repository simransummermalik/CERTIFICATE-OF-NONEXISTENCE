# Building No. 1 Holonomy Lane

## The images

| | File (in `submission/`) |
|---|---|
| 01 · The House, Built Anyway (ink drawing, 18 × 24 in) | `01_Certificate_of_Nonexistence_The_House_Built_Anyway.jpg` |
| 02 · Stair Hall, Looking Down | `02_Certificate_of_Nonexistence_Stair_Hall_Looking_Down.jpg` |
| 03 · Stair Hall, Looking Up | `03_Certificate_of_Nonexistence_Stair_Hall_Looking_Up.jpg` |
| 04 · The Hall | `04_Certificate_of_Nonexistence_The_Hall.jpg` |

Each image also comes as a `*_web.jpg`, 2400 px on its long side, for screens. Lossless PNGs are in `out/images/`. The earlier text plates (the listing, the floor plan and the certificate) are still built by the scripts below and are kept in `out/archive_plates/`.

## Rebuild everything

The Python dependencies are in `.venv`: z3-solver, numpy, Pillow and qrcode. You also need Blender 5.x and `rsvg-convert` (`brew install librsvg`).

```
.venv/bin/python -m nonexistence.prove        # the proof, ~3 min  → out/proof/
.venv/bin/python render/tape.py               # tape-measure texture → out/textures/
./render/batch.sh final "vertigo 4000 256 0.75 50" "hero_a 2400 256 1.5 12" \
                        "hall 2400 256 1.5 1"   # the photographs, ~40 min → out/renders/
.venv/bin/python render/anyway_geometry.py    # the house built anyway: four copies, one level → out/anyway/
/Applications/Blender.app/Contents/MacOS/Blender -b -P render/anyway.py -- --res 7200 --ss 2 --lo -60 --hi 0 \
    --lens 17.5 --cam -91.25 -85.25 140 --look -91.25 -85.25 -1000 --roll -40.2 --shift 0 0.455 \
    --sun 305 34 --out out/anyway/final            # exact passes for the drawing, ~10 min
.venv/bin/python drawings/anyway_ink_strips.py out/anyway/final   # ink, shade and shadow
.venv/bin/python drawings/images.py           # the four images → out/images/, submission/
.venv/bin/python drawings/listing.py          # (archived) Plate I layout
.venv/bin/python drawings/plan.py             # (archived) Plate II
.venv/bin/python drawings/certificate.py      # (archived) Plate III
.venv/bin/python drawings/finish.py           # (archived) the three text plates at 300 dpi
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
| `drawings/finish.py` | Paper, security fibres, black-and-white photo printing |
| `render/anyway_geometry.py` | The four copies of the house, unioned on an exact eighth-inch grid and meshed |
| `render/anyway.py` | Exact passes for the drawing: surface direction, plane, depth, sunlight |
| `drawings/anyway_ink.py`, `anyway_ink_strips.py` | Lines, black cut walls, hatched shade and shadow, fading with depth |
| `drawings/images.py` | The four finished images |
