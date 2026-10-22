#!/usr/bin/env python3
"""FIBO arm: the ten briefs as Fibo 2.0's native structured JSON captions, written by hand here, once, before generation (no Bria API, no caption generator).
Keys follow the model card / diffusers docs: short_description, objects[], background_setting, lighting{}, aesthetics{}, photographic_characteristics{}, style_medium,
context, artistic_style, text_render[{text, location, size, color, font, appearance_details}]. Objects and text entries come from the same boxes as the MOSS layout arm.
Writes prompts/fibo_captions.json (the published file is its output)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t004paths import PROMPTS  # noqa: E402

spec = json.loads((PROMPTS / "briefs.json").read_text(encoding="utf-8"))

SCENE = {
    "b01-hoodie-flat": dict(bg="A pale warm-grey seamless paper backdrop.", light=("soft even studio light", "from above", "very soft and short"),
                            aes=("centered flat lay in a tall portrait frame", "black, orange and warm grey", "clean, premium"),
                            photo=("deep", "sharp over the whole garment", "straight down from above", "50mm"),
                            style="photograph", ctx="A premium e-commerce product photograph.", art="realistic"),
    "b02-hoodie-chest": dict(bg="A softly blurred overcast outdoor background.", light=("soft overcast daylight", "diffuse from above", "soft"),
                             aes=("tight crop from just below the chin to the waist, no face visible, tall portrait frame", "black and orange", "calm, casual"),
                             photo=("shallow", "sharp on the embroidered lettering", "eye level", "50mm"),
                             style="photograph", ctx="A lifestyle fashion photograph.", art="realistic"),
    "b03-lime-hero": dict(bg="A sunny green meadow with soft out-of-focus wildflowers and grass in the foreground and a bright sky.", light=("bright daylight", "from above and slightly behind", "short and crisp"),
                          aes=("the can centered, low camera angle, tall portrait frame", "lime green, yellow, black, cyan and magenta", "fresh, sunny"),
                          photo=("shallow", "sharp on the can label", "low angle", "85mm"),
                          style="photograph", ctx="A soft drink advertising hero shot.", art="realistic"),
    "b04-berry-hero": dict(bg="A pastel pink and blue valley with fresh raspberries and blueberries scattered in the foreground.", light=("soft hazy daylight", "from the front left", "soft"),
                           aes=("the can centered, tall portrait frame", "crimson red, pastel pink and blue, yellow, white, cyan and magenta", "sweet, airy"),
                           photo=("shallow", "sharp on the can label", "slightly low angle", "85mm"),
                           style="photograph", ctx="A soft drink advertising hero shot.", art="realistic"),
    "b05-neon-can500": dict(bg="A near-black seamless backdrop with a puddle of glowing neon slime and glossy droplets frozen in the air.", light=("cyan light from the left and magenta light from the right", "rim lighting from both sides", "deep and soft"),
                            aes=("the can centered, tall portrait frame", "black, cyan, magenta, yellow and white", "loud, futuristic"),
                            photo=("shallow", "sharp on the wordmark", "eye level", "85mm"),
                            style="photograph", ctx="An energy drink product hero shot.", art="realistic"),
    "b06-endcard-lime-berry": dict(bg="A flat off-white paper background.", light=("flat, none", "none", "none"),
                                   aes=("a huge stacked wordmark in the upper half, a yellow band below it, a small footer at the bottom, tall portrait frame", "black, cyan, magenta, yellow on off-white", "bold, clean"),
                                   photo=("none", "flat graphic", "straight on", "none"),
                                   style="graphic design", ctx="An advertising end card.", art="bold print typography"),
    "b07-endcard-hoodie": dict(bg="A flat near-black background.", light=("flat, none", "none", "none"),
                               aes=("a large wordmark in the middle, a subtitle below it, a small footer at the bottom, tall portrait frame", "orange and white on near-black", "minimal, confident"),
                               photo=("none", "flat graphic", "straight on", "none"),
                               style="graphic design", ctx="A fashion advertising end card.", art="clean sans-serif typography"),
    "b08-duo-cans": dict(bg="A seamless light-grey studio backdrop with soft shadows.", light=("soft studio light", "from the front and above", "soft"),
                         aes=("two cans side by side, centered, tall portrait frame", "lime green, crimson red, yellow, black and white", "clean, playful"),
                         photo=("moderate", "sharp on both labels", "eye level", "85mm"),
                         style="photograph", ctx="A studio product photograph of two soda flavours.", art="realistic"),
    "b09-headline-650-72": dict(bg="A flat dark charcoal background.", light=("flat, none", "none", "none"),
                                aes=("a three-line headline, the last line on a yellow band, a thin bar below, tall portrait frame", "white, black and yellow on charcoal", "bold, urgent"),
                                photo=("none", "flat graphic", "straight on", "none"),
                                style="graphic design", ctx="A typographic poster.", art="heavy poster typography"),
    "b10-ai-badge": dict(bg="A flat pale off-white background.", light=("flat, none", "none", "none"),
                         aes=("a wide name plate centered, tall portrait frame", "black, cyan, magenta and yellow on off-white", "clean, editorial"),
                         photo=("none", "flat graphic", "straight on", "none"),
                         style="graphic design", ctx="A broadcast lower-third name plate.", art="clean print design"),
}


def where(box):
    y0, x0, y1, x1 = box
    yc, xc = (y0 + y1) / 2000, (x0 + x1) / 2000
    v = "upper" if yc < 0.36 else ("lower" if yc > 0.64 else "middle")
    h = "left" if xc < 0.36 else ("right" if xc > 0.64 else "center")
    return f"{v} {h} of the frame"


def size_of(box):
    h = (box[2] - box[0]) / 1000
    return "very large" if h > 0.12 else ("large" if h > 0.06 else ("medium" if h > 0.035 else "small"))


COLORS = ["black", "white", "orange", "cyan", "magenta", "yellow", "red"]


def color_of(cap):
    found = [c for c in COLORS if c in cap.lower()]
    return ", ".join(found) if found else "black"


def font_of(cap):
    c = cap.lower()
    if "monospace" in c:
        return "monospaced"
    if "rounded" in c:
        return "rounded sans-serif"
    if "bold" in c or "heavy" in c or "huge" in c:
        return "bold sans-serif"
    return "sans-serif"


out = {}
for b in spec["briefs"]:
    s = SCENE[b["id"]]
    objs = [{"description": el["caption"], "location": where(el["bbox"]), "relative_size": size_of(el["bbox"]) + " within frame"}
            for el in b["layout"] if el["label"] == "object"]
    texts = [{"text": el["text"], "location": where(el["bbox"]), "size": size_of(el["bbox"]), "color": color_of(el["caption"]),
              "font": font_of(el["caption"]), "appearance_details": el["caption"]}
             for el in b["layout"] if el["label"] == "text"]
    cap = {
        "short_description": b["layout_caption"],
        "objects": objs,
        "background_setting": s["bg"],
        "lighting": {"conditions": s["light"][0], "direction": s["light"][1], "shadows": s["light"][2]},
        "aesthetics": {"composition": s["aes"][0], "color_scheme": s["aes"][1], "mood_atmosphere": s["aes"][2]},
        "photographic_characteristics": {"depth_of_field": s["photo"][0], "focus": s["photo"][1], "camera_angle": s["photo"][2], "lens_focal_length": s["photo"][3]},
        "style_medium": s["style"],
        "context": s["ctx"],
        "artistic_style": s["art"],
        "text_render": texts,
    }
    out[b["id"]] = cap
(PROMPTS / "fibo_captions.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("wrote", PROMPTS / "fibo_captions.json")
print(json.dumps(out["b03-lime-hero"], ensure_ascii=False)[:1500])
