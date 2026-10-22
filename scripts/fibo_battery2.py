#!/usr/bin/env python3
"""Battery 2, FIBO 2.0-dev arm (local diffusers, never the Bria API). Derived from fibo_labels.py (imported: the pipeline subclass, the card's t2i negative caption, fonts, the VRAM
sampler) with the memory plan unchanged: encode every caption first, free the Qwen3-VL encoder, then run the 16.3 GB transformer with the stored embeddings. Differences: prompts come from
prompts/battery2.json ('fibo_caption'; BATTERY_SPEC=prompts/battery2_p9.json for p9), the canvas is per prompt (1024x1792 or 1792x1024), and the steps are fixed at 30 (guidance 5.0), the setting the label run ended up with after its 130 s rule.
  FIBO_DIR=/path/to/Fibo-2.0-dev python scripts/fibo_battery2.py SEED [SEED ...]       images -> WORK/images/battery2/fibo/<prompt id>_fibo_<seed>.png ; WORK/results_battery2.jsonl"""
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fibo_labels as FR  # noqa: E402  (imports torch/diffusers; its main() is not run)
import torch  # noqa: E402
from diffusers import BriaFibo2Transformer2DModel, FlowMatchEulerDiscreteScheduler  # noqa: E402
from diffusers.models import AutoencoderKLFlux2  # noqa: E402
from transformers import Qwen3VLForConditionalGeneration, Qwen3VLProcessor  # noqa: E402
from t004paths import PROMPTS as PROMPT_DIR, WORK  # noqa: E402

M = FR.M
RES = WORK / "results_battery2.jsonl"
OUT = WORK / "images" / "battery2" / "fibo"
STEPS = 30
SPEC = json.loads(Path(os.environ.get("BATTERY_SPEC") or PROMPT_DIR / "battery2.json").read_text(encoding="utf-8"))
PR = {p["id"]: p for p in SPEC["prompts"]}
PROMPTS = {k: json.dumps(v["fibo_caption"], ensure_ascii=False) for k, v in PR.items()}


def log(rec):
    with open(RES, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(json.dumps(rec, ensure_ascii=False), flush=True)


def done():
    s = set()
    if RES.exists():
        for line in RES.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r.get("ok") and r.get("phase") == "b2" and r.get("arm") == "fibo":
                s.add((r["brief"], r["seed"]))
    return s


def main(seeds):
    todo = [(pid, s) for s in seeds for pid in PR if (pid, s) not in done()]
    if not todo:
        print("nothing to do")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    vram = FR.G.Vram()
    t0 = time.time()
    te = Qwen3VLForConditionalGeneration.from_pretrained(M / "text_encoder", dtype=torch.bfloat16, device_map="cuda").eval()
    processor = Qwen3VLProcessor.from_pretrained(M / "processor")
    vae = AutoencoderKLFlux2.from_pretrained(M / "vae", dtype=torch.bfloat16).to("cuda")
    sched = FlowMatchEulerDiscreteScheduler.from_pretrained(M / "scheduler")
    pipe = FR.P(transformer=None, scheduler=sched, vae=vae, text_encoder=te, processor=processor)
    print("phase 1 load", round(time.time() - t0, 1), "s", flush=True)
    store, orig = {}, pipe.encode_prompt
    state = {"brief": None, "n": 0, "neg": None, "replay": False}

    def wrapped(*a, **k):
        # Prompts WITHOUT text_render make the pipeline skip the "base" (no text images) encode, so unlike fibo_run.py the calls are told apart by their content:
        # the negative call passes the negative caption; the other calls come in order (main, then base if there is one).
        p0 = a[0] if a else k.get("prompt")
        p0 = p0[0] if isinstance(p0, list) else p0
        is_neg = p0 == FR.NEGATIVE_T2I
        if state["replay"]:
            if is_neg:
                e, m = state["neg"]
            else:
                state["n"] += 1
                e, m = store[state["brief"]][state["n"] - 1]
            return e.to("cuda"), (m.to("cuda") if m is not None else None)
        if is_neg:
            if state["neg"] is not None:
                raise FR.Stop
            e, m = orig(*a, **k)
            state["neg"] = (e.to("cpu"), m.to("cpu") if m is not None else None)
            raise FR.Stop
        e, m = orig(*a, **k)
        store[state["brief"]].append((e.to("cpu"), m.to("cpu") if m is not None else None))
        return e, m

    pipe.encode_prompt = wrapped
    for pid in PR:
        state.update(brief=pid, n=0, replay=False)
        store[pid] = []
        w, h = PR[pid]["canvas"]
        try:
            pipe(prompt=PROMPTS[pid], negative_prompt=FR.NEGATIVE_T2I, width=w, height=h, num_inference_steps=1, guidance_scale=FR.GUIDANCE, fonts=FR.FONTS)
        except FR.Stop:
            pass
        torch.cuda.synchronize()
    log({"phase": "b2-encode", "arm": "fibo", "peak_alloc_gib": round(torch.cuda.max_memory_allocated() / 2**30, 2), "card_peak_mib": vram.peak})
    pipe.text_encoder = None
    del te
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    tr = BriaFibo2Transformer2DModel.from_pretrained(M / "transformer", dtype=torch.bfloat16, device_map="cuda").eval()
    pipe.register_modules(transformer=tr)
    state["replay"] = True
    first = True
    for pid, seed in todo:
        w, h = PR[pid]["canvas"]
        dest = OUT / f"{pid}_fibo_{seed}.png"
        state.update(brief=pid, n=0)
        torch.cuda.reset_peak_memory_stats()
        vr = FR.G.Vram()
        t3 = time.time()
        img = pipe(prompt=PROMPTS[pid], negative_prompt=FR.NEGATIVE_T2I, width=w, height=h, num_inference_steps=STEPS, guidance_scale=FR.GUIDANCE, fonts=FR.FONTS,
                   generator=torch.Generator("cpu").manual_seed(seed)).images[0]
        torch.cuda.synchronize()
        sec = round(time.time() - t3, 2)
        img.save(dest)
        log({"phase": "b2", "arm": "fibo", "brief": pid, "seed": seed, "canvas": [w, h], "file": f"battery2/fibo/{dest.name}", "ok": True, "steps": STEPS, "guidance": FR.GUIDANCE,
             "exec_s": sec, "peak_alloc_gib": round(torch.cuda.max_memory_allocated() / 2**30, 2), "peak_mib": vr.stop(), "cold": first, "t_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        first = False
    vram.stop()
    print("FIBO B2 DONE", flush=True)


if __name__ == "__main__":
    main([int(x) for x in sys.argv[1:]] or [101])
