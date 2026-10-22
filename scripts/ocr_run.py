#!/usr/bin/env python3
"""Reader of record: baidu/Unlimited-OCR (MIT) run locally, greedy decoding, prompt '<image>document parsing.' (the only mode the model card documents;
'Free OCR.' returned junk on our controls). Configurations (picked on the controls only, never on test images):
  c0  whole image, README "gundam" single-image config (base_size 1024, image_size 640, crop_mode True)
  c1  whole image, README "base" config (image_size 1024, crop_mode False)
  c2  overlapping horizontal bands (height 768, step ~512), each parsed with the gundam config, texts concatenated top to bottom
  python scripts/ocr_run.py --model /path/to/Unlimited-OCR --dir DIR --out FILE.json --config c0|c1|c2 [--glob '*.png']
--model (or UNLIMITED_OCR_DIR) is a local copy of huggingface.co/baidu/Unlimited-OCR at revision 8249d20b2822a7d8a4c22c8d8c9069b5ac36bda3.
Needs a CUDA GPU (about 7 GB of weights in bf16). Environment: see README (torch 2.10.0, transformers 4.57.1).
eval_mode=True returns the text and skips the model code's save_results path (that path eval()s model output; never used here).
The run is offline (HF_HUB_OFFLINE=1): the model folder must already be on disk."""
import argparse, glob, json, os, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t004paths import WORK  # noqa: E402
import scoring  # noqa: E402

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
PROMPT = "<image>document parsing."


def bands(w, h, bh=768, step=512):
    if h <= bh:
        return [(0, h)]
    out, y = [], 0
    while True:
        y1 = min(h, y + bh)
        out.append((y1 - bh if y1 - y < bh else y, y1))
        if y1 >= h:
            return out
        y += step


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=os.environ.get("UNLIMITED_OCR_DIR"), help="local folder with the Unlimited-OCR files (or set UNLIMITED_OCR_DIR)")
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--config", default="c0", choices=["c0", "c1", "c2"])
    ap.add_argument("--glob", default="*.png")
    ap.add_argument("--max-length", type=int, default=4096)
    a = ap.parse_args()
    if not a.model:
        sys.exit("give --model /path/to/Unlimited-OCR (or set UNLIMITED_OCR_DIR)")
    MODEL = a.model
    import torch
    from PIL import Image
    from transformers import AutoModel, AutoTokenizer
    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(MODEL, trust_remote_code=True)
    model = AutoModel.from_pretrained(MODEL, trust_remote_code=True, use_safetensors=True, dtype=torch.bfloat16).eval().cuda()
    load_s = round(time.time() - t0, 1)
    print("loaded in", load_s, "s; allocated GiB", round(torch.cuda.memory_allocated() / 2**30, 2), flush=True)
    files = sorted(glob.glob(os.path.join(a.dir, a.glob)))
    out_path = Path(a.out)
    results = json.loads(out_path.read_text()) if out_path.exists() else {"model": os.path.basename(os.path.normpath(MODEL)), "prompt": PROMPT, "config": a.config, "load_s": load_s, "items": {}}
    tmp = WORK / "ocr" / "_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    kw = dict(base_size=1024, image_size=1024, crop_mode=False) if a.config == "c1" else dict(base_size=1024, image_size=640, crop_mode=True)

    def infer(path):
        return model.infer(tok, prompt=PROMPT, image_file=path, output_path=str(tmp), eval_mode=True, max_length=a.max_length,
                           no_repeat_ngram_size=35, ngram_window=128, **kw)

    for f in files:
        name = os.path.basename(f)
        if name in results["items"]:
            continue
        torch.cuda.reset_peak_memory_stats()
        t1 = time.time()
        try:
            if a.config == "c2":
                im = Image.open(f).convert("RGB")
                parts = []
                for i, (y0, y1) in enumerate(bands(*im.size)):
                    p = tmp / f"band{i}.png"
                    im.crop((0, y0, im.size[0], y1)).save(p)
                    parts.append(infer(str(p)))
                raw = "\n".join(parts)
            else:
                raw = infer(f)
            err = None
        except Exception as e:  # keep going: a failure is a result
            raw, err = "", f"{type(e).__name__}: {e}"[:500]
        sec = round(time.time() - t1, 2)
        results["items"][name] = {"raw": raw, "text": scoring.strip_tags(raw).strip(), "seconds": sec,
                                  "peak_alloc_gib": round(torch.cuda.max_memory_allocated() / 2**30, 2), "error": err}
        print(name, sec, "s", repr(results["items"][name]["text"][:80]), err or "", flush=True)
        out_path.write_text(json.dumps(results, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
