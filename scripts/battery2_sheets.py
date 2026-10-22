#!/usr/bin/env python3
"""Battery 2 sheets (CPU, Pillow). Three jobs, all from WORK/images/battery2/<arm>/<prompt id>_<arm>_<seed>.png:

  battery2_sheets.py reading SCRATCH_DIR     sheets for the AI reader's own reading, with a PRIVATE random letter per image (new shuffle per prompt and seed), pages of <= 3 images
                                             (portrait, 640 px wide each) or <= 3 stacked (landscape, 900 px wide). The letter -> arm map is written to SCRATCH_DIR/b2_reading_map.json and is
                                             only read by battery2_score.py: the reader never looks at it, so the ratings are made without knowing which model drew which image.
  battery2_sheets.py blind                   the BLIND ranking set for a human voter -> WORK/battery2_blind/ : for each prompt, seed 101 only, every model's image renamed A..E in a random
                                             order per prompt (metadata stripped by re-saving), one contact sheet per prompt with ONLY the letters, a README without model names, and the key
                                             KEY.json (chmod 600; KEY_<prompt>.json for an extra prompt). Nothing in that folder except the key names a model. The mapping is never printed.
  battery2_sheets.py grids                   named grids -> WORK/grids/battery2/ (or T004_GRIDS) : one per prompt, rows = seeds, columns = models, the model name under every cell and (if
                                             WORK/ocr/battery2_reading.json exists) the AI reader's four scores.
BATTERY_SPEC=prompts/battery2_p9.json selects the extra prompt p9 instead of p1-p8.
Random order = random.SystemRandom (not reproducible on purpose)."""
import json
import os
import random
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t004paths import PROMPTS, WORK, find_font  # noqa: E402

SPEC_FILE = Path(os.environ.get("BATTERY_SPEC") or PROMPTS / "battery2.json")
SPEC = json.loads(SPEC_FILE.read_text(encoding="utf-8"))
PR = {p["id"]: p for p in SPEC["prompts"]}
ARM_ORDER = ["krea-dense", "moss-prompt", "qwen21", "fibo", "qwena", "klein"]
TITLE = {"krea-dense": "Krea 2 Turbo", "moss-prompt": "MOSS-Image", "qwen21": "Qwen-Image-2.1 (NC licence)", "fibo": "Bria FIBO 2.0-dev (NC licence)", "qwena": "Qwen-Image-2512 (Apache-2.0)", "klein": "FLUX 3 Image Klein"}
FB = find_font("DejaVuSans-Bold.ttf")
F = find_font("DejaVuSans.ttf")
RNG = random.SystemRandom()


def img_path(arm, pid, seed):
    return WORK / "images" / "battery2" / arm / f"{pid}_{arm}_{seed}.png"


def arms_for(pid, seed):
    return [a for a in ARM_ORDER if img_path(a, pid, seed).exists()]


def seeds_for(pid):
    return [s for s in SPEC["seeds"] if arms_for(pid, s)]


def font(sz, bold=True):
    return ImageFont.truetype(FB if bold else F, sz)


def fit(d, text, size, maxw, bold=True):
    """largest font size (down to 9) at which `text` fits in maxw pixels; the text is cut if it still does not fit."""
    while size > 9 and d.textlength(text, font=font(size, bold)) > maxw:
        size -= 1
    while text and d.textlength(text, font=font(size, bold)) > maxw:
        text = text[:-1]
    return text, size


def label_box(d, xy, text, size=64):
    x, y = xy
    f = font(size)
    w = int(d.textlength(text, font=f)) + 28
    d.rectangle([x, y, x + w, y + size + 22], fill=(0, 0, 0))
    d.text((x + 14, y + 8), text, fill=(255, 255, 255), font=f)


def reading(scratch):
    scratch = Path(scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    mpf = scratch / "b2_reading_map.json"
    mp = json.loads(mpf.read_text(encoding="utf-8")) if mpf.exists() else {}      # never reshuffle a (prompt, seed) that already has sheets: the ratings by letter depend on it
    for pid, p in PR.items():
        land = p["canvas"][0] > p["canvas"][1]
        for seed in seeds_for(pid):
            if f"{pid}|{seed}" in mp:
                continue
            arms = arms_for(pid, seed)
            order = arms[:]
            RNG.shuffle(order)
            letters = {L: a for L, a in zip("ABCDE", order)}
            mp[f"{pid}|{seed}"] = letters
            per = 3
            items = list(letters.items())
            for k in range(0, len(items), per):
                chunk = items[k:k + per]
                ims = []
                for L, a in chunk:
                    im = Image.open(img_path(a, pid, seed)).convert("RGB")
                    w = 900 if land else 640
                    ims.append((L, im.resize((w, int(im.size[1] * w / im.size[0])), Image.LANCZOS)))
                if land:
                    H = sum(i.size[1] + 8 for _, i in ims)
                    sh = Image.new("RGB", (900, H), "white")
                    y = 0
                    for L, i in ims:
                        sh.paste(i, (0, y))
                        label_box(ImageDraw.Draw(sh), (6, y + 6), L, 40)
                        y += i.size[1] + 8
                else:
                    H = max(i.size[1] for _, i in ims)
                    sh = Image.new("RGB", (640 * len(ims) + 10 * (len(ims) - 1), H), "white")
                    for j, (L, i) in enumerate(ims):
                        sh.paste(i, (j * 650, 0))
                        label_box(ImageDraw.Draw(sh), (j * 650 + 6, 6), L, 40)
                sh.save(scratch / f"b2read_{pid}_{seed}_{k // per + 1}.png")
    (scratch / "b2_reading_map.json").write_text(json.dumps(mp), encoding="utf-8")
    print("reading sheets written to", scratch, "(map not shown)")


def blind():
    out = WORK / "battery2_blind"
    out.mkdir(parents=True, exist_ok=True)
    key = {}
    for pid, p in PR.items():
        arms = arms_for(pid, 101)
        if len(arms) < 2:
            continue
        order = arms[:]
        RNG.shuffle(order)
        short = pid.split("-")[0]                      # p1 ... p9
        letters = {}
        cells = []
        for L, a in zip("ABCDE", order):
            letters[L] = a
            im = Image.open(img_path(a, pid, 101)).convert("RGB")       # re-saved: no PNG text chunks (ComfyUI writes the graph and model names into them)
            im.save(out / f"{short}_{L}.png")
            cells.append((L, im))
        key[short] = {"prompt_id": pid, "letters": letters}
        land = p["canvas"][0] > p["canvas"][1]
        cw = 880 if land else 440
        ims = [(L, im.resize((cw, int(im.size[1] * cw / im.size[0])), Image.LANCZOS)) for L, im in cells]
        cols = 2 if land else len(ims)
        rows = (len(ims) + cols - 1) // cols
        ch = max(i.size[1] for _, i in ims)
        sh = Image.new("RGB", (cols * cw + (cols + 1) * 10, rows * ch + (rows + 1) * 10), (240, 240, 240))
        d = ImageDraw.Draw(sh)
        for j, (L, i) in enumerate(ims):
            x, y = 10 + (j % cols) * (cw + 10), 10 + (j // cols) * (ch + 10)
            sh.paste(i, (x, y))
            label_box(d, (x + 8, y + 8), L, 64)
        sh.save(out / f"{short}_sheet.png")
    if SPEC_FILE.name == "battery2.json":
        (out / "README.md").write_text(
            "# Blind ranking set (battery 2)\n\nFor each prompt p1..p8 there is one contact sheet `pN_sheet.png` with the images labelled by letter only, and the same images one by one as `pN_A.png`, `pN_B.png`, ...\n"
            "The order of the letters is random for each prompt. Please rank each sheet from best to worst (human realism first: faces, hands, skin; then the look of the image) before opening `KEY.json`.\n"
            "The key is `KEY.json` (permissions 600). The prompts are in `prompts/battery2.json`.\n", encoding="utf-8")
    kp = out / ("KEY.json" if SPEC_FILE.name == "battery2.json" else f"KEY_{next(iter(key))}.json")
    kp.write_text(json.dumps(key, indent=1), encoding="utf-8")
    os.chmod(kp, 0o600)
    print("blind set written:", len(key), "prompts; key written (not shown)")


def grids():
    out = Path(os.environ.get("T004_GRIDS") or WORK / "grids" / "battery2")
    out.mkdir(parents=True, exist_ok=True)
    rp = WORK / "ocr" / "battery2_reading.json"
    rd = json.loads(rp.read_text(encoding="utf-8")) if rp.exists() else {}
    for pid, p in PR.items():
        seeds = seeds_for(pid)
        arms = [a for a in ARM_ORDER if any(img_path(a, pid, s).exists() for s in seeds)]
        if not arms:
            continue
        land = p["canvas"][0] > p["canvas"][1]
        many = len(arms) >= 6          # six models: narrower cells keep the sheet readable in a 1600 px wide JPEG
        cw = (440 if many else 600) if land else (320 if many else 360)
        ch = int(cw * p["canvas"][1] / p["canvas"][0])
        cell_h = ch + 84
        sh = Image.new("RGB", (len(arms) * (cw + 10) + 10, 70 + len(seeds) * (cell_h + 10)), (245, 245, 242))
        d = ImageDraw.Draw(sh)
        d.text((10, 8), f"{pid}: {p['intent']}"[:150], fill=(0, 0, 0), font=font(16))
        d.text((10, 36), "AI reading (an AI model, not a person): R realism, A anatomy, C composition, S slop-free (1-5, 5 best). Prompt formats differ by model, intent is the same.", fill=(60, 60, 60), font=font(13, False))
        for r, s in enumerate(seeds):
            for c, a in enumerate(arms):
                x, y = 10 + c * (cw + 10), 70 + r * (cell_h + 10)
                ip = img_path(a, pid, s)
                if ip.exists():
                    sh.paste(Image.open(ip).convert("RGB").resize((cw, ch), Image.LANCZOS), (x, y))
                else:
                    d.rectangle([x, y, x + cw, y + ch], outline=(150, 150, 150), width=3)
                    d.text((x + 20, y + ch // 2), "not run", fill=(120, 120, 120), font=font(20))
                t_, sz_ = fit(d, f"{TITLE[a]} (seed {s})", 14, cw - 4)
                d.text((x + 2, y + ch + 4), t_, fill=(0, 0, 0), font=font(sz_))
                sc = rd.get(f"{pid}_{a}_{s}")
                if sc:
                    d.text((x + 2, y + ch + 24), f"R{sc['realism']} A{sc['anatomy']} C{sc['composition']} S{sc['slop_free']}" + (f"  adherence {sc['adherence']}/5" if 'adherence' in sc else ""), fill=(20, 90, 40), font=font(15))
                    note_, nsz_ = fit(d, sc.get("note", ""), 11, cw - 4, False)
                    d.text((x + 2, y + ch + 46), note_, fill=(120, 60, 0), font=font(nsz_, False))
        sh.save(out / f"{pid}.png")
        print(out / f"{pid}.png")


if __name__ == "__main__":
    m = sys.argv[1] if len(sys.argv) > 1 else ""
    if m == "reading" and len(sys.argv) > 2:
        reading(sys.argv[2])
    elif m == "blind":
        blind()
    elif m == "grids":
        grids()
    else:
        sys.exit(__doc__)
