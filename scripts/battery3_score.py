#!/usr/bin/env python3
"""Battery 3 scoring (CPU, standard library). Inputs: prompts/battery3.json (the rubric, written before generation), WORK/ocr/battery3_reading.json (the AI reading: for each
"<prompt>|<arm>|<seed>" one letter per rubric item, P or F, and a note; an AI model looking at every image and crops, subjective, not a person; the published copy is
results/battery3_reading.json), WORK/results_battery3.jsonl (timing and VRAM), and for h4 the OCR reader of record (WORK/ocr/b3_h4_<arm>_unl_c2.json). An image PASSES only if every
rubric item is P. Writes results_battery3.json and results_battery3_tables.md to OUT.
OCR rule for h4: the shared scorer scripts/scoring.py L1 with the target "FRESH BREAD DAILY 7AM-2PM" (letters and digits only, casefolded, one line or a line break that
splits the target; hyphen and spaces ignored). Before the scorer fix of 2026-10-22 the h4 pass was `GOAL in norm(text)` on the whole text with the lines joined (kept as
`ocr_c2_pass_pre_fix` in the JSON)."""
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import scoring  # noqa: E402  (h4 uses the shared scorer)
from t004paths import OUT, PROMPTS, WORK  # noqa: E402

SPEC = json.loads((PROMPTS / "battery3.json").read_text(encoding="utf-8"))
PROMPTS = {p["id"]: p for p in SPEC["prompts"]}
ARMS = ["krea-dense", "moss-prompt", "qwen21", "fibo", "qwena", "klein"]
TITLE = {"krea-dense": "Krea 2 Turbo (9 st)", "moss-prompt": "MOSS-Image SFT (50 st)", "qwen21": "Qwen-Image-2.1 (40 st)", "fibo": "FIBO 2.0-dev (30 st)", "qwena": "Qwen-Image-2512 (50 st)",
         "klein": "FLUX 3 Image Klein (16 st)"}
R = {}                     # (prompt id, arm, seed) -> (one P/F letter per rubric item, note)
for _k, _v in json.loads((WORK / "ocr" / "battery3_reading.json").read_text(encoding="utf-8")).items():
    _p, _a, _s = _k.split("|")
    R[(_p, _a, int(_s))] = (_v["items"], _v["note"])
GOAL = "FRESHBREADDAILY7AM2PM"
H4_EXPECTED = [{"s": "FRESH BREAD DAILY 7AM-2PM", "min_count": 1}]


def norm(t):
    return "".join(c for c in (t or "").upper() if c.isalnum())


timing = {}
for line in (WORK / "results_battery3.jsonl").read_text(encoding="utf-8").splitlines():
    r = json.loads(line)
    if r.get("phase") == "b3" and r.get("ok"):
        timing[(r["brief"], r["arm"], r["seed"])] = r
ocr = {}
for a in ARMS:
    p = WORK / f"ocr/b3_h4_{a}_unl_c2.json"
    if p.exists():
        for k, v in json.loads(p.read_text(encoding="utf-8"))["items"].items():
            ocr[k] = v["text"]
per = []
for (pid, arm, seed), val in sorted(R.items()):
    letters, note = val if isinstance(val, tuple) else (val, "")
    items = PROMPTS[pid]["rubric"]
    assert len(letters) == len(items), (pid, arm, seed, letters)
    t = timing.get((pid, arm, seed), {})
    e = dict(prompt=pid, arm=arm, seed=seed, file=f"images/battery3/{arm}/{pid}_{arm}_{seed}.png", items=dict(zip([i.split(" ")[0] for i in items], [c == "P" for c in letters])),
             to_pass=all(c == "P" for c in letters), note=note, exec_s=t.get("exec_s"), peak_mib=t.get("peak_mib"), cold=t.get("cold"))
    e["pass"] = e.pop("to_pass")
    if pid.startswith("h4"):
        txt = ocr.get(f"{pid}_{arm}_{seed}.png")
        e["ocr_c2_text"] = txt
        e["ocr_c2_pass"] = scoring.check(txt, H4_EXPECTED, True)[1] if txt is not None else None
        e["ocr_c2_pass_pre_fix"] = (GOAL in norm(txt)) if txt is not None else None
    per.append(e)
out = dict(spec="prompts/battery3.json", reader="AI visual reading (subjective, one AI reader, not a person); OCR c2 (Unlimited-OCR) for h4", per_image=per)
by_arm = {a: {} for a in ARMS}
for e in per:
    by_arm[e["arm"]].setdefault(e["prompt"], []).append(e)
summary = {}
for a in ARMS:
    n = sum(len(v) for v in by_arm[a].values())
    ok = sum(x["pass"] for v in by_arm[a].values() for x in v)
    secs = [x["exec_s"] for v in by_arm[a].values() for x in v if x["exec_s"] and not x["cold"]]
    summary[a] = dict(passes=ok, n=n, per_prompt={p: f"{sum(x['pass'] for x in v)}/{len(v)}" for p, v in by_arm[a].items()},
                      median_warm_s=round(statistics.median(secs), 1) if secs else None,
                      peak_mib=max([x["peak_mib"] for v in by_arm[a].values() for x in v if x["peak_mib"]] or [0]))
out["summary"] = summary
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "results_battery3.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
L = ["# Battery 3, hard prompts: results (AI reading, subjective; h4 also OCR c2)", "",
     "An image passes only if every rubric item passes. Rubric: prompts/battery3.json (written before generation). Cells = passes / images (seeds 101, 102).", ""]
hdr = "| Model | total | " + " | ".join(PROMPTS) + " | median warm s | peak MiB |"
L += [hdr, "|" + "---|" * (hdr.count("|") - 1)]
for a in ARMS:
    s = summary[a]
    if not s["n"]:
        continue
    L.append(f"| {TITLE[a]} | **{s['passes']}/{s['n']}** | " + " | ".join(s["per_prompt"].get(p, "n/a") for p in PROMPTS) + f" | {s['median_warm_s']} | {s['peak_mib']} |")
L += ["", "## Per image (items R1..: P/F; note = what went wrong)", ""]
for pid in PROMPTS:
    L += [f"### {pid}: {PROMPTS[pid]['intent']}", "", "Rubric: " + " | ".join(PROMPTS[pid]["rubric"]), ""]
    for e in per:
        if e["prompt"] != pid:
            continue
        its = "".join("P" if v else "F" for v in e["items"].values())
        extra = ""
        if pid.startswith("h4"):
            extra = f" | OCR c2: {'PASS' if e['ocr_c2_pass'] else 'FAIL' if e['ocr_c2_pass'] is not None else 'n/a'} `{(e['ocr_c2_text'] or '')[:80].strip()!r}`"
        L.append(f"- {TITLE[e['arm']]} seed {e['seed']}: **{'PASS' if e['pass'] else 'FAIL'}** [{its}] {e['note']}{extra}")
    L.append("")
(OUT / "results_battery3_tables.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L[:14]))
