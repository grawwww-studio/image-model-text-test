#!/usr/bin/env python3
"""FIBO has no ComfyUI graph (ComfyUI 0.42.1 only has Bria's cloud API nodes; we call none of them), so its "workflow shot" is a rendered diagram of the
local diffusers pipeline that scripts/fibo_labels.py runs. It is labelled as a diagram, not a ComfyUI screenshot.
  fibo_diagram.py [OUT.png]      default WORK/workflow_fibo_diagram.png; reads the step count from WORK/results_fibo.jsonl if it exists (else 50)"""
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t004paths import WORK, find_font  # noqa: E402

FB = find_font("DejaVuSans-Bold.ttf")
F = find_font("DejaVuSans.ttf")
steps = "50"
res = WORK / "results_fibo.jsonl"
if res.exists():
    st = {json.loads(l).get("steps") for l in res.read_text(encoding="utf-8").splitlines() if '"phase": "test"' in l}
    st.discard(None)
    if st:
        steps = "/".join(str(s) for s in sorted(st))
W, H = 1900, 760
im = Image.new("RGB", (W, H), (30, 30, 34))
d = ImageDraw.Draw(im)
f = lambda s, b=False: ImageFont.truetype(FB if b else F, s)
d.text((40, 24), "Bria FIBO 2.0-dev: local diffusers pipeline (BriaFibo2Pipeline)", fill=(240, 240, 240), font=f(30, True))
d.text((40, 66), "DIAGRAM rendered from the script, not a ComfyUI screenshot: no ComfyUI graph exists for this model (ComfyUI's Bria nodes call Bria's cloud API; none was used).", fill=(255, 190, 90), font=f(20))
boxes = [
    (40, 150, 430, 250, "Structured JSON caption", "VGL fields + text_render list", "by hand: prompts/fibo_captions.json", (70, 110, 170)),
    (40, 330, 430, 430, "text_render glyph images", "each text drawn with Aileron,", "then DejaVu Sans (the pipeline draws them)", (70, 110, 170)),
    (520, 240, 900, 340, "Qwen3-VL-4B text encoder", "bf16, 8.9 GB (8 875 719 408 B)", "loaded alone first, then freed", (120, 90, 170)),
    (990, 240, 1330, 340, "Perceiver -> gist tokens", "+ 5 blocks read Qwen3-VL directly", "(gated cross-attention)", (120, 90, 170)),
    (1420, 200, 1840, 380, "Fibo 2.0 transformer", "8.1B flow-matching, bf16, 16.3 GB", f"{steps} steps, guidance 5.0, 1024x1792", "50 steps measured: 136 s per image", "negative = card's t2i negative caption", (50, 140, 100)),
    (1420, 480, 1840, 580, "FLUX.2 VAE decode", "336 MB", "-> PNG", (50, 140, 100)),
]
for b in boxes:
    x0, y0, x1, y1 = b[:4]
    d.rounded_rectangle([x0, y0, x1, y1], radius=10, fill=b[-1], outline=(235, 235, 235), width=2)
    d.text((x0 + 14, y0 + 10), b[4], fill=(255, 255, 255), font=f(22, True))
    for i, t in enumerate(b[5:-1]):
        d.text((x0 + 14, y0 + 44 + i * 24), t, fill=(235, 235, 235), font=f(17))


def arrow(a, b):
    d.line([a, b], fill=(235, 235, 235), width=3)
    ax, ay = b
    d.polygon([(ax, ay), (ax - 14, ay - 8), (ax - 14, ay + 8)] if b[0] > a[0] else [(ax, ay), (ax - 8, ay - 14), (ax + 8, ay - 14)], fill=(235, 235, 235))


arrow((430, 200), (520, 270))
arrow((430, 380), (520, 310))
arrow((900, 290), (990, 290))
arrow((1330, 290), (1420, 290))
arrow((1630, 380), (1630, 480))
d.text((40, 640), "Memory plan: encoder and transformer do not fit together on the 24 GB card (8.9 + 16.3 GB), so every caption is encoded first (same three encode_prompt calls the pipeline makes),", fill=(200, 200, 200), font=f(18))
d.text((40, 668), "the embeddings are kept on the CPU, the encoder is freed, then the transformer runs with the stored embeddings. Same maths as the stock pipeline.", fill=(200, 200, 200), font=f(18))
d.text((40, 710), "Weights local only, revision 530604492bf2bd1364ae43ca6b2bf2285ef0f2ba. Licence: CC BY-NC 4.0 per the model card (commercial use needs an agreement with Bria): see NOTICE.md.", fill=(255, 190, 90), font=f(18))
out = Path(sys.argv[1]) if len(sys.argv) > 1 else WORK / "workflow_fibo_diagram.png"
out.parent.mkdir(parents=True, exist_ok=True)
im.save(out)
print(out)
