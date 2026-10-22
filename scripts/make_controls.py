#!/usr/bin/env python3
"""Reader controls, the rendered part (CPU, Pillow): text images 1024x1792 with the exact label strings (positives) and one-character corruptions of them
(negatives). A reader must pass every positive and fail every negative. Writes WORK/controls/<id>_pos.png and <id>_neg.png and checks them against
prompts/controls.json (the published list of all controls). The other controls in that list are real pack shots of fictional products (b01, b03, b04, b05;
not included) and, in prompts/controls_real.json, ten generated images judged by the AI reading (not included).
Needs the DejaVu Sans fonts (Debian/Ubuntu: fonts-dejavu-core), or set T004_FONT_DIR to the folder that holds DejaVuSans-Bold.ttf and DejaVuSansMono.ttf."""
import json
import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t004paths import PROMPTS, WORK, find_font  # noqa: E402

OUT = WORK / "controls"
OUT.mkdir(parents=True, exist_ok=True)


BOLD = find_font("DejaVuSans-Bold.ttf")
MONO = find_font("DejaVuSansMono.ttf")
W, H = 1024, 1792

# (id, expected strings, lines shown for the positive, lines shown for the negative, bg, fg, font, size)
CASES = [
    ("c01", [("GRAWWWW", 1)], ["GRA", "WWWW"], ["GRA", "WWW"], (120, 190, 60), (20, 20, 20), BOLD, 260),
    ("c02", [("GRAWWWW", 1)], ["GRA", "WWWW"], ["GRA", "WWWWW"], (200, 30, 70), (255, 255, 255), BOLD, 250),
    ("c03", [("LIME", 1)], ["LIME"], ["LIMF"], (255, 214, 0), (20, 20, 20), BOLD, 280),
    ("c04", [("BERRY", 1)], ["BERRY"], ["BERY"], (255, 214, 0), (20, 20, 20), BOLD, 230),
    ("c05", [("grawwww", 1)], ["grawwww"], ["grawwwv"], (30, 30, 30), (240, 110, 20), BOLD, 160),
    ("c06", [("650 S TO 72 S", 1)], ["650 S", "TO", "72 S"], ["650 S", "TO", "27 S"], (40, 40, 44), (255, 255, 255), BOLD, 250),
    ("c07", [("LARA", 1), ("AI-GENERATED PRESENTER", 1)], ["LARA", "AI-GENERATED PRESENTER"], ["LAKA", "AI-GENERATED PRESENTOR"], (245, 245, 240), (15, 15, 15), BOLD, 200),
    ("c08", [("LIME · BERRY", 1)], ["LIME · BERRY"], ["LIME · BERY"], (255, 214, 0), (20, 20, 20), BOLD, 120),
    ("c09", [("washed black hoodie", 1)], ["washed black hoodie"], ["washed black hoodle"], (15, 15, 15), (255, 255, 255), BOLD, 80),
    ("c10", [("AI-generated · fictional product and brand", 1)], ["AI-generated · fictional", "product and brand"], ["AI-generated · fictional", "product and brnad"], (245, 245, 240), (15, 15, 15), MONO, 60),
    ("c11", [("GRAWWWW", 2)], ["GRA", "WWWW", "", "GRA", "WWWW"], ["GRA", "WWWW", "", "GRA", "WWW"], (225, 225, 220), (20, 20, 20), BOLD, 200),
    ("c12", [("grawwww", 1)], ["grawwww"], ["grawww"], (20, 20, 20), (240, 110, 20), BOLD, 70),   # small text, like the embroidery
]


def render(lines, bg, fg, font, size):
    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(font, size)
    while max(d.textlength(t, font=f) for t in lines) > W * 0.88 and size > 20:
        size -= 6
        f = ImageFont.truetype(font, size)
    lh = int(size * 1.25)
    y = (H - lh * len(lines)) // 2
    for t in lines:
        w = d.textlength(t, font=f)
        d.text(((W - w) / 2, y), t, font=f, fill=fg)
        y += lh
    return im


published = {r["file"]: r for r in json.loads((PROMPTS / "controls.json").read_text(encoding="utf-8"))}
for cid, exp, pos, neg, bg, fg, font, size in CASES:
    for kind, lines in (("pos", pos), ("neg", neg)):
        f = f"{cid}_{kind}.png"
        render(lines, bg, fg, font, size).save(OUT / f)
        row = published[f]
        assert row["kind"] == kind and row["shown"] == " / ".join(lines) and row["expected"] == [{"s": s, "min_count": n} for s, n in exp], f
print(len(CASES) * 2, "rendered control images ->", OUT, "(checked against prompts/controls.json)")
