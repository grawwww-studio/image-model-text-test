#!/usr/bin/env python3
"""Per-brief comparison grids of the label test (CPU, Pillow): one sheet per brief with the arms side by side for seed 101 and one with all three seeds.
Every cell shows the image, the arm, a frame and PASS/FAIL from the AI reading, the PASS/FAIL of the reader of record (Unlimited-OCR, config c2) and the
expected label strings. Reads results.json and results_extra.json from OUT (written by final_score.py and score_extra.py) and the images from WORK.

  make_label_grids.py [--out DIR] [arm ...]     default arms: the four first ones plus every extra arm that has images (qwen21, fibo, qwena, klein).
                                                Name some extra arms to leave the others out, e.g. `make_label_grids.py qwen21 qwena` leaves FIBO out.
Writes DIR/<brief>_seed101.png and DIR/<brief>_allseeds.png (default DIR = WORK/grids). The sheets in this repository's grids/labels/ are these, reduced
(reduce_grids.py)."""
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t004paths import OUT, PROMPTS, WORK, find_font  # noqa: E402

FROZEN = ["krea-dense", "krea-ie", "moss-prompt", "moss-layout"]
EXTRA = ["qwen21", "fibo", "qwena", "klein"]
ARM_TITLE = {"krea-dense": "Krea 2 dense prompt", "krea-ie": "Krea 2 + Ident. Edit (pack)", "moss-prompt": "MOSS prompt-only", "moss-layout": "MOSS layout JSON",
             "qwen21": "Qwen-Image-2.1 (NC licence)", "fibo": "Bria FIBO 2.0-dev (NC licence)", "qwena": "Qwen-Image-2512 (Apache-2.0)",
             "klein": "FLUX 3 Image Klein"}
F = find_font("DejaVuSans.ttf")
FB = find_font("DejaVuSans-Bold.ttf")
OK, BAD, NA = (30, 150, 60), (200, 40, 40), (140, 140, 140)


def font(sz, bold=False):
    return ImageFont.truetype(FB if bold else F, sz)


def image_path(arm, name):
    return (WORK / "images" / arm / name) if arm in EXTRA else (WORK / "images" / name)


def cell(res_by_file, spec_b, arm, seed, cw):
    ch = int(cw * 1792 / 1024)
    name = f"{spec_b['id']}_{arm}_{seed}.png"
    im = Image.new("RGB", (cw, ch + 150), "white")
    d = ImageDraw.Draw(im)
    r = res_by_file.get(name)
    p = image_path(arm, name)
    title, size = ARM_TITLE[arm] + f"  (seed {seed})", 15
    while d.textlength(title, font=font(size, True)) > cw - 10 and size > 10:
        size -= 1
    d.text((6, 4), title, fill=(0, 0, 0), font=font(size, True))
    if r is None or not p.exists():
        d.rectangle([0, 28, cw - 1, ch + 28], outline=NA, width=4)
        d.text((cw // 2 - 70, ch // 2), "not applicable" if arm == "krea-ie" else "missing", fill=NA, font=font(20, True))
        return im
    pic = Image.open(p).convert("RGB").resize((cw - 8, ch - 8 + 0), Image.LANCZOS)
    col = OK if r.get("agent_read") else BAD
    im.paste(pic, (4, 32))
    d.rectangle([0, 28, cw - 1, ch + 32], outline=col, width=5)
    y = ch + 38
    d.text((6, y), "AI READING: " + ("PASS" if r.get("agent_read") else "FAIL"), fill=col, font=font(16, True))
    y += 21
    g = r.get("unl_c2")
    d.text((6, y), "OCR (Unlimited-OCR c2): " + ("PASS" if g else "FAIL"), fill=OK if g else BAD, font=font(14, True))
    y += 19
    for s in spec_b["strings"]:
        t = "label: " + s["s"] + (f" (x{s['min_count']})" if s["min_count"] > 1 else "")
        while t and d.textlength(t, font=font(13)) > cw - 10:
            t = t[:-1]
        d.text((6, y), t, fill=(40, 40, 40), font=font(13))
        y += 16
    if r.get("agent_note"):
        note = r["agent_note"]
        while note and d.textlength(note, font=font(11)) > cw - 10:
            note = note[:-1]
        d.text((6, y), note, fill=(120, 60, 0), font=font(11))
    return im


def grids(arms, out_dir):
    orig = json.loads((OUT / "results.json").read_text(encoding="utf-8"))["per_image"]
    extra = [e for e in json.loads((OUT / "results_extra.json").read_text(encoding="utf-8"))["per_image"] if e["arm"] in arms]
    merged = orig + [dict(e, file=Path(e["file"]).name) for e in extra]
    missing = [e["file"] for e in merged if "agent_read" not in e]
    if missing:
        sys.exit(f"no AI reading for {len(missing)} images, e.g. {missing[:3]}")
    by_file = {r["file"]: r for r in merged}
    spec = json.loads((PROMPTS / "briefs.json").read_text(encoding="utf-8"))
    out_dir.mkdir(parents=True, exist_ok=True)
    cw = 300
    for b in spec["briefs"]:
        for seeds, tag in (([101], "seed101"), ([101, 102, 103], "allseeds")):
            rows = [[cell(by_file, b, a, s, cw) for a in arms] for s in seeds]
            ch = rows[0][0].size[1]
            W = cw * len(arms) + 10 * (len(arms) + 1)
            H = 60 + len(rows) * (ch + 10)
            sheet = Image.new("RGB", (W, H), (245, 245, 242))
            d = ImageDraw.Draw(sheet)
            d.text((10, 8), f"{b['id']}  -  {b['source'][:110]}", fill=(0, 0, 0), font=font(16, True))
            d.text((10, 32), "label strings: " + "  |  ".join(s["s"] for s in b["strings"]), fill=(40, 40, 40), font=font(14))
            for ri, cells in enumerate(rows):
                for ci, c in enumerate(cells):
                    sheet.paste(c, (10 + ci * (cw + 10), 60 + ri * (ch + 10)))
            out = out_dir / f"{b['id']}_{tag}.png"
            sheet.save(out)
            print(out)


if __name__ == "__main__":
    args = sys.argv[1:]
    out_dir = WORK / "grids"
    if "--out" in args:
        i = args.index("--out")
        out_dir = Path(args[i + 1])
        args = args[:i] + args[i + 2:]
    extra = args or [a for a in EXTRA if (WORK / "images" / a).is_dir() and any((WORK / "images" / a).glob("*.png"))]
    for a in extra:
        if a not in EXTRA:
            sys.exit(f"unknown extra arm {a}; extra arms: {', '.join(EXTRA)}")
    grids(FROZEN + extra, out_dir)
