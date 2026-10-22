#!/usr/bin/env python3
"""Battery 2 scoring (CPU, standard library). The AI reader's ratings are written by letter (the private shuffled letters of battery2_sheets.py reading) in
WORK/ocr/battery2_reading_by_letter.json: {"<prompt id>|<seed>": {"A": {"realism": 1-5, "anatomy": 1-5, "composition": 1-5, "slop_free": 1-5, "adherence": 0-5 (p7 only), "note": "..."}, ...}}.
This script maps the letters to arms with the private map (SCRATCH_DIR/b2_reading_map.json), writes WORK/ocr/battery2_reading.json (keyed <prompt id>_<arm>_<seed>), and writes
results_battery2.json and results_battery2_tables.md to OUT: mean score per arm and criterion, per prompt, and time / whole-card VRAM from WORK/results_battery2.jsonl.
Klein was read on its own pages (klein seed 101, klein seed 102 and one Krea 2 image as a calibration anchor, private letters, map SCRATCH_DIR/b2k_map.json, ratings in
WORK/ocr/battery2_reading_klein_by_letter.json); only Klein's ratings join the tables, the anchor is a check that the 1-5 scale held.
Scores are an AI model's reading, subjective, 1-5 with 5 best (slop_free 5 = no slop look). A person's blind ranking (battery2_sheets.py blind) is separate.
Only prompts that have a spec file in prompts/ are scored; readings of any other prompt in the by-letter files are ignored.
  battery2_score.py SCRATCH_DIR"""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t004paths import OUT, PROMPTS, WORK  # noqa: E402

if len(sys.argv) < 2:
    sys.exit(__doc__)
scratch = Path(sys.argv[1])
SPEC = json.loads((PROMPTS / "battery2.json").read_text(encoding="utf-8"))
PIDS = [p["id"] for p in SPEC["prompts"]]
PIDS8 = PIDS[:]            # the frozen battery (p1-p8): the means below stay over these, so numbers reported before p9 keep their meaning
for _f in sorted(PROMPTS.glob("battery2_p[0-9]*.json")):       # extra prompts (p9): own rows, own timing section
    PIDS += [p["id"] for p in json.loads(_f.read_text(encoding="utf-8"))["prompts"]]
EXTRA = [x for x in PIDS if x not in PIDS8]
EXTRA9 = [x for x in EXTRA if x.startswith("p9")]
ARMS = ["krea-dense", "moss-prompt", "qwen21", "fibo", "qwena", "klein"]
CRIT = ["realism", "anatomy", "composition", "slop_free"]
byl = json.loads((WORK / "ocr" / "battery2_reading_by_letter.json").read_text(encoding="utf-8"))
mp = json.loads((scratch / "b2_reading_map.json").read_text(encoding="utf-8"))
reading = {}
for k, letters in byl.items():
    pid, seed = k.split("|")
    for L, sc in letters.items():
        arm = mp[k][L]
        reading[f"{pid}_{arm}_{seed}"] = sc
_kp, _km = WORK / "ocr" / "battery2_reading_klein_by_letter.json", scratch / "b2k_map.json"
if _kp.exists() and _km.exists():      # Klein: own letters (klein 101, klein 102 and one krea-dense anchor per page); only Klein's ratings join the table, anchors are a calibration check
    _kmap = json.loads(_km.read_text(encoding="utf-8"))
    for k, letters in json.loads(_kp.read_text(encoding="utf-8")).items():
        pid = k.split("|")[0]
        for L, sc in letters.items():
            arm_seed = _kmap[k][L]
            if arm_seed.startswith("klein_"):
                reading[f"{pid}_{arm_seed}"] = sc
reading = {k: v for k, v in reading.items() if k.split("_")[0] in PIDS}          # prompts without a spec file in prompts/ are left out
(WORK / "ocr" / "battery2_reading.json").write_text(json.dumps(reading, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

rows = [json.loads(l) for l in (WORK / "results_battery2.jsonl").read_text(encoding="utf-8").splitlines()] if (WORK / "results_battery2.jsonl").exists() else []
test = [r for r in rows if r.get("phase") == "b2" and r.get("ok")]
res = {"note": "AI reading (an AI model, not a person). 1-5, 5 best. Subjective.", "arms": {}}
for arm in ARMS:
    allkeys = [k for k in reading if f"_{arm}_" in k]
    keys = [k for k in allkeys if k.split("_")[0] in PIDS8]
    if not allkeys and not any(r["arm"] == arm for r in test):
        continue
    a = {"images_read": len(keys), "mean": {c: round(statistics.mean(reading[k][c] for k in keys), 2) for c in CRIT} if keys else {}, "per_prompt": {}}
    for pid in PIDS:
        ks = [k for k in allkeys if k.startswith(pid + "_")]
        if ks:
            a["per_prompt"][pid] = {c: round(statistics.mean(reading[k][c] for k in ks), 2) for c in CRIT}
            if pid.startswith("p7"):
                a["per_prompt"][pid]["adherence"] = round(statistics.mean(reading[k]["adherence"] for k in ks), 2)
    a["overall"] = round(statistics.mean(statistics.mean(reading[k][c] for c in CRIT) for k in keys), 2) if keys else None
    for ex in EXTRA:
        kx = [k for k in allkeys if k.startswith(ex + "_")]
        if kx:
            a.setdefault("overall_extra", {})[ex] = round(statistics.mean(statistics.mean(reading[k][c] for c in CRIT) for k in kx), 2)
    a["human_realism_mean"] = round(statistics.mean(statistics.mean(reading[k][c] for c in ("realism", "anatomy")) for k in keys if k.split("_")[0] in ("p1-presenter", "p2-hands-can", "p3-elderly-man", "p4-cafe-four")), 2) if any(k.split("_")[0] in ("p1-presenter", "p2-hands-can", "p3-elderly-man", "p4-cafe-four") for k in keys) else None
    rs9 = [r for r in test if r["arm"] == arm and r["brief"] in EXTRA9]       # "timing_extra" keeps its p9-only meaning (numbers reported on 2026-10-20 unchanged)
    if rs9:
        w9 = [r["exec_s"] for r in rs9 if not r.get("cold")]
        a["timing_extra"] = {"prompts": EXTRA9, "images": len(rs9), "warm_median_s": round(statistics.median(w9), 2) if w9 else None, "cold_first_s": [r["exec_s"] for r in rs9 if r.get("cold")],
                             "all_s": [r["exec_s"] for r in rs9], "total_s": round(sum(r["exec_s"] for r in rs9), 1), "peak_mib_max": max(r["peak_mib"] for r in rs9)}
    for ex in EXTRA:        # timing per extra prompt
        rx = [r for r in test if r["arm"] == arm and r["brief"] == ex]
        if rx:
            wx = [r["exec_s"] for r in rx if not r.get("cold")]
            a.setdefault("timing_by_extra", {})[ex] = {"images": len(rx), "warm_median_s": round(statistics.median(wx), 2) if wx else None, "cold_first_s": [r["exec_s"] for r in rx if r.get("cold")],
                                                       "all_s": [r["exec_s"] for r in rx], "total_s": round(sum(r["exec_s"] for r in rx), 1), "peak_mib_max": max(r["peak_mib"] for r in rx)}
    rs = [r for r in test if r["arm"] == arm and r["brief"] in PIDS8]
    if rs:
        warm = [r["exec_s"] for r in rs if not r.get("cold")]
        pk = [r["peak_mib"] for r in rs]
        a["timing"] = {"images": len(rs), "warm_median_s": round(statistics.median(warm), 2) if warm else None, "warm_min_s": min(warm) if warm else None, "warm_max_s": max(warm) if warm else None,
                       "cold_first_s": [r["exec_s"] for r in rs if r.get("cold")], "total_s": round(sum(r["exec_s"] for r in rs), 1),
                       "peak_mib_max": max(pk), "peak_gib_max": round(max(pk) / 1024, 2), "peak_mib_median": int(statistics.median(pk))}
    res["arms"][arm] = a
res["reading"] = reading
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "results_battery2.json").write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

md = ["# Battery 2: tables (generated by scripts/battery2_score.py; AI reading, subjective)", "",
      "## Mean of the AI reading per model over the frozen battery p1-p8 (1-5, 5 best; S = slop-free; extra prompts such as p9 have their own section below)", "", "| model | images | realism | anatomy | composition | slop-free | overall | human-prompts realism+anatomy (p1-p4) |", "|---|---|---|---|---|---|---|---|"]
for arm, a in res["arms"].items():
    m = a["mean"]
    md.append(f"| {arm} | {a['images_read']} | {m.get('realism')} | {m.get('anatomy')} | {m.get('composition')} | {m.get('slop_free')} | {a['overall']} | {a['human_realism_mean']} |")
md += ["", "## Per prompt (mean over seeds of realism / anatomy / composition / slop-free; p7 also adherence facts out of 5)", "", "| prompt | " + " | ".join(res["arms"]) + " |", "|---|" + "---|" * len(res["arms"])]
for pid in PIDS:
    cells = []
    for arm, a in res["arms"].items():
        pp = a["per_prompt"].get(pid)
        cells.append("n/a" if not pp else " / ".join(str(pp[c]) for c in CRIT) + (f" ; adh {pp['adherence']}/5" if "adherence" in pp else ""))
    md.append(f"| {pid} | " + " | ".join(cells) + " |")
md += ["", "## Time and VRAM (ComfyUI execution time for the ComfyUI models; wall time of the diffusers call for fibo; whole-card nvidia-smi peak, includes ~2.1 GiB of other idle residents)", "",
       "| model | images | warm s/img median (min-max) | cold first s | peak MiB (GiB) max | peak MiB median | total s |", "|---|---|---|---|---|---|---|"]
for arm, a in res["arms"].items():
    t = a.get("timing")
    if t:
        md.append(f"| {arm} | {t['images']} | {t['warm_median_s']} ({t['warm_min_s']}-{t['warm_max_s']}) | {t['cold_first_s']} | {t['peak_mib_max']} ({t['peak_gib_max']}) | {t['peak_mib_median']} | {t['total_s']} |")
for ex in EXTRA:        # one section per extra prompt (p9)
    md += ["", "## Extra prompt " + ex + ": AI reading mean over seeds (realism / anatomy / composition / slop-free), overall, and time (the first image of a model's run is cold; whole-card VRAM peak)", "",
           "| prompt | model | images | realism / anatomy / composition / slop-free | overall | s/img (all images in order) | warm median s | peak MiB (GiB) max |", "|---|---|---|---|---|---|---|---|"]
    for arm, a in res["arms"].items():
        pp, tx = a["per_prompt"].get(ex), a.get("timing_by_extra", {}).get(ex)
        if pp or tx:
            n = sum(1 for k in reading if k.startswith(ex + "_" + arm + "_"))
            md.append(f"| {ex} | {arm} | {n} | " + (" / ".join(str(pp[c]) for c in CRIT) if pp else "n/a") + f" | {a.get('overall_extra', {}).get(ex, 'n/a')} | " +
                      (f"{tx['all_s']} | {tx['warm_median_s']} | {tx['peak_mib_max']} ({round(tx['peak_mib_max'] / 1024, 2)})" if tx else "n/a | n/a | n/a") + " |")
(OUT / "results_battery2_tables.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print("\n".join(md))
