#!/usr/bin/env python3
"""Validity of a reader on the controls (rendered strings and pack shots: prompts/controls.json; realistic generated images with the AI reading as truth:
prompts/controls_real.json), by scoring.py L1 and the pre-registered rule.
  gate_eval.py NAME prompts/controls.json:runs/ocr/controls_unl_c2.json prompts/controls_real.json:runs/ocr/controlsreal_unl_c2.json
Prints sensitivity (truth-positive passed), specificity (truth-negative rejected), balanced accuracy and the validity verdict (>= 0.80 and >= 0.90)."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import scoring


def load(spec_file, ocr_file):
    spec = {r["file"]: r for r in json.load(open(spec_file))}
    ocr = json.load(open(ocr_file))["items"]
    rows = []
    for f, r in spec.items():
        if f not in ocr:
            continue
        truth = r.get("truth_pass", r.get("kind") == "pos")
        res, ok = scoring.check(ocr[f]["text"], r["expected"], True)
        rows.append((f, truth, ok, ocr[f]["text"]))
    return rows


def evaluate(name, pairs, verbose=False):
    rows = []
    for p in pairs:
        s, o = p.split(":")
        rows += load(s, o)
    tp = sum(1 for _, t, o, _ in rows if t and o)
    P = sum(1 for _, t, _, _ in rows if t)
    tn = sum(1 for _, t, o, _ in rows if (not t) and (not o))
    N = sum(1 for _, t, _, _ in rows if not t)
    sens, spec = tp / P if P else float("nan"), tn / N if N else float("nan")
    print(f"{name}: sens {tp}/{P} = {sens:.2f}  spec {tn}/{N} = {spec:.2f}  balanced {(sens + spec) / 2:.2f}  valid={'YES' if sens >= 0.8 and spec >= 0.9 else 'NO'}")
    if verbose:
        for f, t, o, txt in rows:
            if t != o:
                print("   MISS" if t else "   FALSE-PASS", f, repr(txt[:70]))
    return sens, spec


if __name__ == "__main__":
    name = sys.argv[1]
    evaluate(name, sys.argv[2:], verbose=True)
