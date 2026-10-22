#!/usr/bin/env python3
"""FIBO 2.0 Dev in NATIVE ComfyUI. The native nodes (FIBO model, text encoder, TextEncodeFibo2) were added to ComfyUI by pull request #17240 (merged 2026-10-21, commit
87ed5a066d9c4660ef42100fd01a888da6994856), after 0.42.1: use a ComfyUI that contains that commit. (We ran 0.42.1 with the 13 files of that commit overlaid.) Files = the Comfy-Org/Fibo-2.0
repack, Dev only: diffusion_models/fibo2_dev_{int8_convrot,bf16}.safetensors, text_encoders/qwen3vl_4b_{int8_convrot,bf16}.safetensors, vae/flux2-vae.safetensors.
Graph: UNETLoader -> KSampler (30 steps, cfg 5.0, euler/simple = the PR's Dev settings and our diffusers run), CLIPLoader type fibo2, TextEncodeFibo2 (prompt = the SAME structured JSON
caption as the diffusers run, negative = the model card's t2i negative caption, the same as the diffusers run), VAELoader, VAEDecode. Size 1024x1792 (b07) and 1792x1024 (p6) set on the node.
  fibo_comfy_run.py run [int8_convrot|bf16 ...]   b07-endcard-hoodie seed 101 then p6-night-rain seed 101 per variant -> WORK/images/fibo_comfy/<variant>/<prompt>_<seed>.png ; WORK/results_fibo_comfy.jsonl
  fibo_comfy_run.py workflows [DIR]                write workflow_fibo_comfyui_api.json (bf16, b07; default DIR = the current folder): the file in workflows/comfyui/
Standard library only. Environment: COMFY_URL, T004_WORK, T004_VRAM=0."""
import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_comfy as G  # noqa: E402
from t004paths import PROMPTS, WORK  # noqa: E402

RESULTS = WORK / "results_fibo_comfy.jsonl"
NEG = re.search(r"NEGATIVE_T2I = \('(.*?)'\)", (HERE / "fibo_labels.py").read_text(encoding="utf-8"), re.S).group(1)
VARIANTS = {"int8_convrot": ("fibo2_dev_int8_convrot.safetensors", "qwen3vl_4b_int8_convrot.safetensors"),
            "bf16": ("fibo2_dev_bf16.safetensors", "qwen3vl_4b_bf16.safetensors")}
STEPS, CFG = 30, 5.0


def cases():
    cap = json.loads((PROMPTS / "fibo_captions.json").read_text(encoding="utf-8"))
    p6 = [p for p in json.loads((PROMPTS / "battery2.json").read_text(encoding="utf-8"))["prompts"] if p["id"].startswith("p6")][0]
    return [("b07-endcard-hoodie", json.dumps(cap["b07-endcard-hoodie"], ensure_ascii=False), 1024, 1792, 101),
            ("p6-night-rain", json.dumps(p6["fibo_caption"], ensure_ascii=False), 1792, 1024, 101)]


def graph(variant, caption, w, h, seed, prefix):
    unet, te = VARIANTS[variant]
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": unet, "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": te, "type": "fibo2", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "flux2-vae.safetensors"}},
        "4": {"class_type": "TextEncodeFibo2", "inputs": {"clip": ["2", 0], "prompt": caption, "negative_prompt": NEG, "width": w, "height": h, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["4", 0], "negative": ["4", 1], "latent_image": ["4", 2], "seed": seed, "steps": STEPS, "cfg": CFG,
              "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["3", 0]}},
        "7": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": prefix}},
    }


def run(variants):
    for v in variants:
        n = 0
        for pid, cap, w, h, seed in cases():
            dest = WORK / "images" / "fibo_comfy" / v / f"{pid}_{seed}.png"
            r = G.run_graph(graph(v, cap, w, h, seed, f"t004c/{pid}_{v}_{seed}"), timeout=1800)
            if r["ok"]:
                G.fetch(r["images"][0], dest)
            G.log(RESULTS, dict(phase="fibo-comfy", arm=f"fibo-comfy-{v}", brief=pid, seed=seed, canvas=[w, h], steps=STEPS, cfg=CFG, file=f"fibo_comfy/{v}/{dest.name}", ok=r["ok"], exec_s=r["exec_s"],
                       wall=r["wall"], peak_mib=r["peak_mib"], cold=(n == 0), prompt_id=r["prompt_id"], error=r["error"], t_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
            n += 1
    G.cmd_free()


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else ""
    if c == "run":
        run(sys.argv[2:] or list(VARIANTS))
    elif c == "workflows":
        pid, cap, w, h, seed = cases()[0]
        out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".")
        out.mkdir(parents=True, exist_ok=True)
        (out / "workflow_fibo_comfyui_api.json").write_text(json.dumps(graph("bf16", cap, w, h, seed, "t004c/workflow"), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("wrote", out)
    else:
        sys.exit(__doc__)
