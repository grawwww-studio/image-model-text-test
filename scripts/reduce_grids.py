#!/usr/bin/env python3
"""Reduce comparison grids for publication: every PNG in SRC becomes a JPEG at most MAX_WIDTH pixels wide (default 1600, Lanczos), quality 85, in DST.
  reduce_grids.py SRC DST [MAX_WIDTH] [QUALITY]
The grids in this repository are the output of make_label_grids.py and battery2_sheets.py grids, reduced with this script. No full-size image is published."""
import sys
from pathlib import Path
from PIL import Image

if len(sys.argv) < 3:
    sys.exit(__doc__)
src, dst = Path(sys.argv[1]), Path(sys.argv[2])
max_w = int(sys.argv[3]) if len(sys.argv) > 3 else 1600
quality = int(sys.argv[4]) if len(sys.argv) > 4 else 85
dst.mkdir(parents=True, exist_ok=True)
for p in sorted(src.glob("*.png")):
    im = Image.open(p).convert("RGB")
    if im.size[0] > max_w:
        im = im.resize((max_w, round(im.size[1] * max_w / im.size[0])), Image.LANCZOS)
    out = dst / (p.stem + ".jpg")
    im.save(out, "JPEG", quality=quality, optimize=True)
    print(out.name, im.size, round(out.stat().st_size / 1024), "KB")
