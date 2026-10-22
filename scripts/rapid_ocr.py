#!/usr/bin/env python3
"""Secondary OCR (CPU): RapidOCR 1.2.3 (Apache-2.0, PP-OCRv3 ONNX). A literal CTC reader, so it does not auto-correct garbled text the way an
LLM-based OCR can. Cross-check only; the reader of record is Unlimited-OCR (ocr_run.py).
  pip install rapidocr_onnxruntime==1.2.3
  rapid_ocr.py DIR OUT.json [glob]"""
import glob, json, os, sys, time
from rapidocr_onnxruntime import RapidOCR

d, out = sys.argv[1], sys.argv[2]
pat = sys.argv[3] if len(sys.argv) > 3 else "*.png"
ocr = RapidOCR()
res = json.load(open(out)) if os.path.exists(out) else {"model": "rapidocr_onnxruntime 1.2.3 PP-OCRv3", "items": {}}
for f in sorted(glob.glob(os.path.join(d, pat))):
    n = os.path.basename(f)
    if n in res["items"]:
        continue
    t = time.time()
    r, _ = ocr(f)
    lines = [x[1] for x in (r or [])]
    res["items"][n] = {"text": "\n".join(lines), "seconds": round(time.time() - t, 2), "error": None}
    print(n, repr(" | ".join(lines))[:100], flush=True)
    json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
