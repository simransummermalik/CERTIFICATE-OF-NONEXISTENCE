"""Texture for the inspector's tape measure: 0 to 38′-7″, sixteenths of an inch."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PX_PER_IN = 128
INCHES = 480                 # four rows of 120 inches each (GPU textures max out at 16384 px)
ROW_IN = 120
ROWS = 4
H = 128
OUT = Path(__file__).resolve().parent.parent / "out" / "textures" / "tape.png"

YELLOW = (236, 190, 38)
BLACK = (18, 16, 12)
RED = (196, 38, 30)


def strip():
    im = Image.new("RGB", (INCHES * PX_PER_IN, H), YELLOW)
    d = ImageDraw.Draw(im)
    f_big = ImageFont.truetype("/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf", 64)
    f_small = ImageFont.truetype("/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf", 30)
    for i in range(INCHES * 16):
        x = i * PX_PER_IN / 16
        L = {0: 46}.get(i % 16, 34 if i % 8 == 0 else 26 if i % 4 == 0 else 18 if i % 2 == 0 else 12)
        d.line([(x, 0), (x, L)], fill=BLACK, width=4 if i % 16 == 0 else 2)
        d.line([(x, H - 1), (x, H - 1 - L * 0.5)], fill=BLACK, width=2)
    for inch in range(1, INCHES):
        x = inch * PX_PER_IN
        if inch % 12 == 0:
            ft = inch // 12
            d.rectangle([x - 44, 50, x + 44, 112], fill=RED)
            d.text((x, 82), f"{ft}F", font=f_big, fill=YELLOW, anchor="mm")
        else:
            d.text((x - 4, 84), str(inch), font=f_big, fill=BLACK, anchor="rm")
            if inch % 16 == 0:
                d.polygon([(x - 10, 118), (x + 10, 118), (x, 104)], fill=BLACK)
    d.text((20, 100), "HOLONOMY", font=f_small, fill=BLACK, anchor="lm")
    return im


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    long = strip()
    w = ROW_IN * PX_PER_IN
    im = Image.new("RGB", (w, H * ROWS), YELLOW)
    for r in range(ROWS):
        im.paste(long.crop((r * w, 0, (r + 1) * w, H)), (0, r * H))
    im.save(OUT, optimize=True)
    print(OUT, im.size)


if __name__ == "__main__":
    main()
