#!/usr/bin/env python3
"""Battery 3 helper (Pillow).
  battery3_sheets.py read PROMPT_ID SEED        blind reading sheet: the arms present for that prompt and seed, private shuffled letters (key saved to
                                                WORK/battery3/KEY_read.json, mode 600, written once per prompt+seed and then reused), cells 640 px wide, labelled by letter only
                                                -> SCRATCH/b3read_<prompt>_<seed>_<page>.png ; prints the paths
  battery3_sheets.py cropL PROMPT_ID SEED LETTERS x0,y0,x1,y1   the same box cut from the images of those letters, side by side (the arm names are never printed)
  battery3_sheets.py crop PROMPT_ID SEED ARM x0,y0,x1,y1        enlarged crop of one image (in the image's own pixels) -> SCRATCH/b3crop_<prompt>_<arm>_<seed>.png
  battery3_sheets.py grids                      named grids, one per prompt, for publication: rows = seeds, models labelled, the AI reading's PASS or FAIL under each image
                                                and, when it failed, a one-line note; for h4 also the verdict of the OCR reader of record. Reads OUT/results_battery3.json.
                                                Portrait prompts: six columns; landscape prompts: three columns, two rows per seed. Written to WORK/grids/battery3/ (or T004_GRIDS),
                                                about 1600 px wide: reduce them with reduce_grids.py.
SCRATCH is WORK/scratch (or T004_SCRATCH). Random letters come from random.SystemRandom (not reproducible; the key file is the record)."""
import json
import os
import random
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t004paths import OUT, PROMPTS, WORK, find_font  # noqa: E402

S = Path(os.environ.get("T004_SCRATCH") or WORK / "scratch")
S.mkdir(parents=True, exist_ok=True)
SPEC = json.loads((PROMPTS / "battery3.json").read_text(encoding="utf-8"))
SPEC_BY_ID = {p["id"]: p for p in SPEC["prompts"]}
ARMS = ["krea-dense", "moss-prompt", "qwen21", "fibo", "qwena", "klein"]
TITLE = {"krea-dense": "Krea 2 Turbo", "moss-prompt": "MOSS-Image SFT", "qwen21": "Qwen-Image-2.1", "fibo": "FIBO 2.0-dev (30 st)", "qwena": "Qwen-Image-2512", "klein": "FLUX 3 Image Klein"}
KEY = WORK / "battery3" / "KEY_read.json"
FONT = find_font("DejaVuSans-Bold.ttf")


def font(n):
    try:
        return ImageFont.truetype(FONT, n)
    except OSError:
        return ImageFont.load_default()


def img(arm, pid, seed):
    p = WORK / "images" / "battery3" / arm / f"{pid}_{arm}_{seed}.png"
    return Image.open(p).convert("RGB") if p.exists() else None


def key():
    return json.loads(KEY.read_text(encoding="utf-8")) if KEY.exists() else {}


def read(pid, seed):
    k = key()
    kk = f"{pid}_{seed}"
    arms = [a for a in ARMS if img(a, pid, seed) is not None]
    if kk not in k:
        letters = list("ABCDEF"[:len(arms)])
        random.SystemRandom().shuffle(letters)
        k[kk] = dict(zip(letters, arms))
        KEY.parent.mkdir(parents=True, exist_ok=True)
        KEY.write_text(json.dumps(k, indent=1), encoding="utf-8")
        KEY.chmod(0o600)
    m = k[kk]
    land = SPEC_BY_ID[pid]["canvas"][0] > SPEC_BY_ID[pid]["canvas"][1]
    cells = []
    for L in sorted(m):
        im = img(m[L], pid, seed)
        w = 640
        im = im.resize((w, int(im.size[1] * w / im.size[0])), Image.LANCZOS)
        cells.append((L, im))
    per_page = 6 if land else 3          # landscape: 3x2 on one page; portrait: one row of 3 per page (cells stay readable)
    outs = []
    for pg, start in enumerate(range(0, len(cells), per_page), 1):
        chunk = cells[start:start + per_page]
        cols = 3
        rows = [chunk[i:i + cols] for i in range(0, len(chunk), cols)]
        cw = 640
        sheet_w = cols * cw + (cols + 1) * 8
        sheet_h = sum(max(c[1].size[1] for c in r) + 32 for r in rows) + 8
        sheet = Image.new("RGB", (sheet_w, sheet_h), "white")
        d = ImageDraw.Draw(sheet)
        y = 8
        for r in rows:
            for i, (L, im) in enumerate(r):
                x = 8 + i * (cw + 8)
                d.text((x + 4, y + 2), L, fill=(0, 0, 0), font=font(24))
                sheet.paste(im, (x, y + 30))
            y += max(c[1].size[1] for c in r) + 32
        out = S / f"b3read_{pid}_{seed}_{pg}.png"
        sheet.save(out)
        outs.append(out)
    print(*outs, "arms", len(cells))


def cropL(pid, seed, letters, box):
    """blind crops: LETTERS (e.g. ACF) of the reading sheet of (pid, seed), same box for each, stacked side by side (max ~1900 px wide); the arm names are never printed."""
    m = key()[f"{pid}_{seed}"]
    x0, y0, x1, y1 = [int(v) for v in box.split(",")]
    cells = []
    for L in letters:
        c = img(m[L], pid, seed).crop((x0, y0, x1, y1))
        cells.append((L, c))
    cw = min(940, 1900 // len(cells))
    ims = []
    for L, c in cells:
        sc = cw / c.size[0]
        ims.append((L, c.resize((cw, int(c.size[1] * sc)), Image.LANCZOS)))
    H = max(i.size[1] for _, i in ims) + 30
    sh = Image.new("RGB", (cw * len(ims) + 8 * (len(ims) - 1), H), "white")
    d = ImageDraw.Draw(sh)
    for j, (L, i) in enumerate(ims):
        sh.paste(i, (j * (cw + 8), 30))
        d.text((j * (cw + 8) + 4, 2), L, fill=(0, 0, 0), font=font(24))
    out = S / f"b3cropL_{pid}_{seed}_{letters}.png"
    sh.save(out)
    print(out, sh.size)


def crop(pid, seed, arm, box):
    im = img(arm, pid, seed)
    x0, y0, x1, y1 = [int(v) for v in box.split(",")]
    c = im.crop((x0, y0, x1, y1))
    sc = min(1500 / c.size[0], 1500 / c.size[1])
    c = c.resize((int(c.size[0] * sc), int(c.size[1] * sc)), Image.LANCZOS)
    out = S / f"b3crop_{pid}_{arm}_{seed}.png"
    c.save(out)
    print(out, c.size)


def fit(d, text, size, maxw):
    """text cut to maxw pixels at the given font size."""
    while text and d.textlength(text, font=font(size)) > maxw:
        text = text[:-1]
    return text


def wrap(d, text, size, maxw, n):
    """text split at spaces into at most n lines that fit maxw pixels; the last line is cut if the text does not fit."""
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font(size)) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    lines = [x for x in lines if x][:n]
    return [fit(d, x, size, maxw) for x in lines]


def grids():
    res = {}
    rp = OUT / "results_battery3.json"
    if rp.exists():
        for e in json.loads(rp.read_text(encoding="utf-8"))["per_image"]:
            res[(e["prompt"], e["arm"], e["seed"])] = e
    out = Path(os.environ.get("T004_GRIDS") or WORK / "grids" / "battery3")
    out.mkdir(parents=True, exist_ok=True)
    for p in SPEC["prompts"]:
        pid = p["id"]
        landscape = p["canvas"][0] > p["canvas"][1]
        cols = 3 if landscape else 6
        cw = 520 if landscape else 258
        ch = int(cw * p["canvas"][1] / p["canvas"][0])
        seeds = [101, 102]
        rows_per_seed = len(ARMS) // cols
        cell_h = 24 + ch + 22 + 44                       # title, image, verdict bar, two note lines
        W = 8 + cols * (cw + 8)
        head = 64
        H = head + len(seeds) * rows_per_seed * (cell_h + 6) + 8
        sheet = Image.new("RGB", (W, H), (250, 250, 250))
        d = ImageDraw.Draw(sheet)
        d.text((10, 6), fit(d, f"Battery 3 / {pid}: {p['intent']}", 18, W - 20), fill=(0, 0, 0), font=font(18))
        rule = "Pass rule (every item): " + "; ".join(p["rubric"])
        d.text((10, 32), fit(d, rule, 12, W - 20), fill=(60, 60, 60), font=font(12))
        d.text((10, 48), fit(d, rule[len(fit(d, rule, 12, W - 20)):], 12, W - 20), fill=(60, 60, 60), font=font(12))
        y = head
        for s in seeds:
            for rr in range(rows_per_seed):
                for i in range(cols):
                    a = ARMS[rr * cols + i]
                    x = 8 + i * (cw + 8)
                    d.text((x + 2, y), fit(d, f"{TITLE[a]}  seed {s}", 14, cw - 4), fill=(0, 0, 0), font=font(14))
                    im = img(a, pid, s)
                    if im is None:
                        d.rectangle((x, y + 24, x + cw, y + 24 + ch), outline=(180, 180, 180))
                        d.text((x + 10, y + 40), "not run", fill=(120, 120, 120), font=font(16))
                    else:
                        sheet.paste(im.resize((cw, ch), Image.LANCZOS), (x, y + 24))
                    e = res.get((pid, a, s))
                    if e is not None:
                        ok = e["pass"]
                        d.rectangle((x, y + 24 + ch + 2, x + cw, y + 24 + ch + 20), fill=(40, 150, 60) if ok else (190, 50, 50))
                        d.text((x + 6, y + 24 + ch + 4), ("PASS" if ok else "FAIL") + "  (AI reading)", fill=(255, 255, 255), font=font(13))
                        lines = []
                        if e.get("ocr_c2_pass") is not None:
                            lines.append("OCR c2: " + ("PASS" if e["ocr_c2_pass"] else "FAIL"))
                        if not ok and e.get("note"):
                            lines += wrap(d, e["note"], 11, cw - 6, 2 - len(lines))
                        for k, line in enumerate(lines[:2]):
                            d.text((x + 2, y + 24 + ch + 24 + 15 * k), line, fill=(120, 20, 20) if not (line.startswith("OCR c2: PASS")) else (20, 110, 40), font=font(11))
                y += cell_h + 6
        sheet.save(out / f"{pid}.png")
    print("grids ->", out)


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else ""
    if c == "read":
        read(sys.argv[2], int(sys.argv[3]))
    elif c == "cropL":
        cropL(sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5])
    elif c == "crop":
        crop(sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5])
    elif c == "grids":
        grids()
    else:
        sys.exit(__doc__)
