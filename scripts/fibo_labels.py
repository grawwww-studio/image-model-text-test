#!/usr/bin/env python3
"""FIBO arm of the label test (informational, not part of the pre-registered criterion): Bria Fibo 2.0 Dev (briaai/Fibo-2.0-dev, CC BY-NC 4.0 per its model card),
local diffusers BriaFibo2Pipeline, 10 briefs x 3 seeds, 1024x1792, native structured JSON captions (prompts/fibo_captions.json, written by hand). Never the Bria API.

  FIBO_DIR=/path/to/Fibo-2.0-dev python scripts/fibo_labels.py          (FIBO_STEPS=30 to skip the step rule below)
FIBO_DIR is a local copy of huggingface.co/briaai/Fibo-2.0-dev at revision 530604492bf2bd1364ae43ca6b2bf2285ef0f2ba (gated: accept its terms yourself and read them first).
Needs a CUDA GPU with 24 GB. Environment: see README (torch 2.10.0, transformers 5.20.2, diffusers from git commit de988b7ee77c393a63865d265d19e267ef9c7bf5).
Memory plan (the card has 8.1B transformer 16.3 GB + Qwen3-VL-4B encoder 8.9 GB = 25 GB, more than the 24 GB card): phase 1 loads the encoder + VAE on the GPU and
runs the pipeline's own encode_prompt for every brief (same three calls __call__ makes: caption with the text images, caption without them, negative caption), keeping
the embeddings on the CPU; the encoder is then freed, the transformer is loaded on the GPU, and the unmodified pipeline __call__ runs with encode_prompt replaying the
stored embeddings. Same maths as the stock pipeline, only the order of loading differs.
Steps: model card says 50 (guidance 5.0). Rule fixed before the run: if the first image (b03 seed 101) takes more than 130 s at 50 steps, the whole arm runs at 30 steps
(the diffusers default for this checkpoint) and that first image is discarded. Resumable; one line per image in WORK/results_fibo.jsonl."""
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ["TRANSFORMERS_OFFLINE"] = "1"
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import torch  # noqa: E402
import gen_comfy as G  # noqa: E402  (Vram sampler; stdlib only)
from t004paths import PROMPTS, WORK  # noqa: E402
from diffusers import BriaFibo2Pipeline, BriaFibo2Transformer2DModel, FlowMatchEulerDiscreteScheduler  # noqa: E402
from diffusers.models import AutoencoderKLFlux2  # noqa: E402
from transformers import Qwen3VLForConditionalGeneration, Qwen3VLProcessor  # noqa: E402

M = Path(os.environ.get("FIBO_DIR") or WORK / "fibo" / "model")
OUT = WORK / "images" / "fibo"
RES = WORK / "results_fibo.jsonl"
W, H = 1024, 1792
GUIDANCE = 5.0
NEGATIVE_T2I = ('{"short_description":"","objects":[{"description":"the main subject","texture":"smooth, featureless, plastic-like, airbrushed, no fine surface detail","appearance_details":"soft blurred edges, simplified shapes, no fine detail","skin_tone_and_texture":"waxy airbrushed skin, poreless, plastic smooth"}],"background_setting":"a plain seamless studio backdrop, perfectly smooth gradient, blurred and featureless, no visible texture","lighting":{},"aesthetics":{"artifacts":["oversaturated colours","neon colour cast","overexposed highlights","lens flare","slight blur","motion blur","haze"]},"photographic_characteristics":{"depth_of_field":"shallow, heavy bokeh obscuring most of the frame","focus":"soft, slightly out of focus, lacking fine texture"},"style_medium":"","context":"","artistic_style":""}')  # the model card's text-to-image negative, verbatim
FONTS = [str(M / "fonts" / "Aileron-Regular.otf"), str(M / "fonts" / "DejaVuSans.ttf")]


class P(BriaFibo2Pipeline):
    @property
    def _execution_device(self):          # no offload hooks here: everything runs on the one GPU
        return torch.device("cuda")


class Stop(Exception):
    pass


def log(rec):
    with open(RES, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(json.dumps({k: rec[k] for k in rec if k not in ("caption",)}, ensure_ascii=False), flush=True)


def done():
    s = set()
    if RES.exists():
        for line in RES.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r.get("ok") and r.get("phase") == "test":
                s.add((r["brief"], r["seed"]))
    return s


def main():
    spec = json.loads((PROMPTS / "briefs.json").read_text(encoding="utf-8"))
    caps = json.loads((PROMPTS / "fibo_captions.json").read_text(encoding="utf-8"))
    prompts = {b["id"]: json.dumps(caps[b["id"]], ensure_ascii=False) for b in spec["briefs"]}
    OUT.mkdir(parents=True, exist_ok=True)
    todo = [(b["id"], s) for b in spec["briefs"] for s in spec["seeds"] if (b["id"], s) not in done()]
    if not todo:
        print("nothing to do")
        return
    vram = G.Vram()
    t0 = time.time()
    te = Qwen3VLForConditionalGeneration.from_pretrained(M / "text_encoder", dtype=torch.bfloat16, device_map="cuda").eval()
    processor = Qwen3VLProcessor.from_pretrained(M / "processor")
    vae = AutoencoderKLFlux2.from_pretrained(M / "vae", dtype=torch.bfloat16).to("cuda")
    sched = FlowMatchEulerDiscreteScheduler.from_pretrained(M / "scheduler")
    pipe = P(transformer=None, scheduler=sched, vae=vae, text_encoder=te, processor=processor)
    print("phase 1 load", round(time.time() - t0, 1), "s", flush=True)

    # ---- phase 1: embeddings with the pipeline's own encode_prompt, in the order __call__ asks for them
    store = {}                                            # brief -> [(embeds_cpu, mask_cpu), x3]
    orig = pipe.encode_prompt
    state = {"brief": None, "n": 0, "neg": None, "replay": False}

    def wrapped(*a, **k):
        state["n"] += 1
        n = state["n"]
        if state["replay"]:
            e, m = store[state["brief"]][n - 1] if n < 3 else state["neg"]
            return e.to("cuda"), (m.to("cuda") if m is not None else None)
        if n == 3 and state["neg"] is not None:
            raise Stop
        e, m = orig(*a, **k)
        rec = (e.to("cpu"), m.to("cpu") if m is not None else None)
        if n < 3:
            store[state["brief"]].append(rec)
        else:
            state["neg"] = rec
            raise Stop
        return e, m

    pipe.encode_prompt = wrapped
    timings = {}
    for b in spec["briefs"]:
        state.update(brief=b["id"], n=0, replay=False)
        store[b["id"]] = []
        t1 = time.time()
        try:
            pipe(prompt=prompts[b["id"]], negative_prompt=NEGATIVE_T2I, width=W, height=H, num_inference_steps=1, guidance_scale=GUIDANCE, fonts=FONTS)
        except Stop:
            pass
        torch.cuda.synchronize()
        timings[b["id"]] = round(time.time() - t1, 2)
        print("encoded", b["id"], timings[b["id"]], "s", flush=True)
    phase1 = {"peak_alloc_gib": round(torch.cuda.max_memory_allocated() / 2**30, 2), "card_peak_mib": vram.peak, "encode_s": timings}
    log({"phase": "encode", **phase1})
    pipe.text_encoder = None
    del te
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()

    # ---- phase 2: transformer on the GPU, stock __call__ with the stored embeddings
    t2 = time.time()
    tr = BriaFibo2Transformer2DModel.from_pretrained(M / "transformer", dtype=torch.bfloat16, device_map="cuda").eval()
    pipe.register_modules(transformer=tr)
    print("transformer loaded", round(time.time() - t2, 1), "s", flush=True)
    state["replay"] = True
    steps = int(os.environ.get("FIBO_STEPS", "50"))
    adaptive = "FIBO_STEPS" not in os.environ
    first = True
    queue = list(todo)
    while queue:
        brief, seed = queue.pop(0)
        if adaptive and first:
            brief, seed = "b03-lime-hero", 101                 # the smoke image of the step rule (not removed from the queue if it is a test image)
            queue = [x for x in todo if x != (brief, seed)] if (brief, seed) in todo else queue
        dest = OUT / f"{brief}_fibo_{seed}.png"
        state.update(brief=brief, n=0)
        torch.cuda.reset_peak_memory_stats()
        vr = G.Vram()
        t3 = time.time()
        img = pipe(prompt=prompts[brief], negative_prompt=NEGATIVE_T2I, width=W, height=H, num_inference_steps=steps, guidance_scale=GUIDANCE, fonts=FONTS,
                   generator=torch.Generator("cpu").manual_seed(seed)).images[0]
        torch.cuda.synchronize()
        sec = round(time.time() - t3, 2)
        card = vr.stop()
        if adaptive and first and steps == 50 and sec > 130:
            log({"phase": "smoke", "brief": brief, "seed": seed, "steps": 50, "seconds": sec, "ok": True, "note": "slower than 130 s: the arm runs at 30 steps"})
            steps, adaptive, first = 30, False, False
            queue = list(todo)
            continue
        img.save(dest)
        log({"phase": "test", "arm": "fibo", "brief": brief, "seed": seed, "file": dest.name, "ok": True, "steps": steps, "guidance": GUIDANCE, "exec_s": sec,
             "peak_alloc_gib": round(torch.cuda.max_memory_allocated() / 2**30, 2), "card_peak_mib": card, "cold": first,
             "t_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        first = False
    vram.stop()
    print("FIBO DONE", flush=True)


if __name__ == "__main__":
    main()
