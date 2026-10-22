#!/usr/bin/env python3
"""Scoring of the extra arms (CPU, standard library). Same rules as final_score.py (PREREG.md): scoring.py letter-and-digit whole-run match with min_count, image-level pass,
rerolls = failing seeds before the first pass in order 101 102 103 (no pass in 3 = 3, censored), reader of record = Unlimited-OCR c2. Reads results.json
(the four first arms, in OUT; scored with the fixed scoring.py, Addendum 3 of PREREG.md) and the raw reader output in WORK, writes results_extra.json and results_extra_tables.md to OUT. The MOSS-vs-Krea verdict is NOT recomputed here.
Extra arms: fibo, qwen21, qwena (any that has images). Readers: unl_c2 (record), unl_c0, unl_c1, rapid (CPU cross-check, if its JSON exists), agent_read
(ocr/agent_reading_extra.json, an AI model's own reading, not a person). The vision-model reader (vlm) was not run for the extra arms (not measured).
The frozen rule applied to an extra arm (>= the reference arm on >= 8 of 10 briefs AND fewer total rerolls) is reported as information, never as a verdict of record."""
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import scoring  # noqa: E402
from t004paths import OUT, PROMPTS, WORK  # noqa: E402

SEEDS = [101, 102, 103]
spec = json.loads((PROMPTS / "briefs.json").read_text(encoding="utf-8"))
BR = {b["id"]: b for b in spec["briefs"]}
ALL_B = [b["id"] for b in spec["briefs"]]
EXTRA = [a for a in ("qwen21", "fibo", "qwena", "klein") if (WORK / "images" / a).is_dir() and any((WORK / "images" / a).glob("*.png"))]
ORIG_ARMS = ["krea-dense", "krea-ie", "moss-prompt", "moss-layout"]
READERS = ["unl_c2", "unl_c0", "unl_c1", "rapid", "agent_read"]


def J(p):
    return json.loads((p if isinstance(p, Path) else WORK / p).read_text(encoding="utf-8"))


orig = J(OUT / "results.json")["per_image"]
P = {r: {} for r in READERS}            # reader -> file -> bool
T = {r: {} for r in READERS}            # reader -> file -> text
for e in orig:
    for r in READERS:
        if r in e:
            P[r][e["file"]] = e[r]
    T["unl_c2"][e["file"]] = e.get("unl_c2_text")
agent = J("ocr/agent_reading_extra.json") if (WORK / "ocr/agent_reading_extra.json").exists() else {}
notes = {}
files = {}
for arm in EXTRA:
    ocr = {}
    for c in ("c0", "c1", "c2"):
        p = WORK / f"ocr/extra_{arm}_unl_{c}.json"
        if p.exists():
            ocr["unl_" + c] = J(f"ocr/extra_{arm}_unl_{c}.json")["items"]
    p = WORK / f"ocr/extra_{arm}_rapid.json"
    if p.exists():
        ocr["rapid"] = J(f"ocr/extra_{arm}_rapid.json")["items"]
    for b in ALL_B:
        for s in SEEDS:
            n = f"{b}_{arm}_{s}.png"
            if not (WORK / "images" / arm / n).exists():
                continue
            files[n] = arm
            for r, items in ocr.items():
                if n in items:
                    P[r][n] = scoring.check(items[n]["text"], BR[b]["strings"], True)[1]
                    T[r][n] = items[n]["text"]
            if n in agent:
                P["agent_read"][n] = agent[n]["pass"]
                notes[n] = agent[n].get("note", "")


def per_brief(passmap, arms):
    out = {}
    for b in ALL_B:
        for arm in arms:
            names = [f"{b}_{arm}_{s}.png" for s in SEEDS if f"{b}_{arm}_{s}.png" in passmap]
            if not names:
                continue
            rows = [passmap[n] for n in names]
            rr, cens = 0, True
            for ok in rows:
                if ok:
                    cens = False
                    break
                rr += 1
            out.setdefault(b, {})[arm] = {"pass": sum(rows), "n": len(rows), "rate": sum(rows) / len(rows), "rerolls": rr, "censored": cens}
    return out


def compare(pb, arms, ref_arm):
    """the frozen rule (>= ref on >= 8 of 10 briefs AND fewer total rerolls), with `arms` = the arm(s) whose best per brief is taken."""
    rows, mr, kr, ok_n = [], 0, 0, 0
    for b in ALL_B:
        if ref_arm not in pb.get(b, {}) or not any(a in pb[b] for a in arms):
            continue
        m_rate = max(pb[b][a]["rate"] for a in arms if a in pb[b])
        m_rr = min(pb[b][a]["rerolls"] for a in arms if a in pb[b])
        k = pb[b][ref_arm]
        ok_n += m_rate >= k["rate"]
        mr += m_rr
        kr += k["rerolls"]
        rows.append({"brief": b, "arm_rate": round(m_rate, 2), "ref_rate": round(k["rate"], 2), "ge": m_rate >= k["rate"], "arm_rerolls": m_rr, "ref_rerolls": k["rerolls"]})
    return {"arms": arms, "ref": ref_arm, "n": len(rows), "arm_ge_ref_on": ok_n, "arm_rerolls": mr, "ref_rerolls": kr, "rows": rows,
            "rule_would_read": "PASS" if (len(rows) == 10 and ok_n >= 8 and mr < kr) else "FAIL"}


# ------------------------------------------------------------ timing
def timing(arm):
    rows = []
    if arm == "fibo":
        p = WORK / "results_fibo.jsonl"
        if p.exists():
            for l in p.read_text(encoding="utf-8").splitlines():
                r = json.loads(l)
                if r.get("phase") == "test" and r.get("ok"):
                    rows.append(dict(exec_s=r["exec_s"], peak_mib=r["card_peak_mib"], cold=r.get("cold"), steps=r.get("steps")))
    else:
        for l in (WORK / "results_extra.jsonl").read_text(encoding="utf-8").splitlines():
            r = json.loads(l)
            if r.get("arm") == arm and r.get("phase") == "test" and r.get("ok"):
                rows.append(dict(exec_s=r["exec_s"], peak_mib=r["peak_mib"], cold=r.get("cold")))
    if not rows:
        return None
    smoke = None
    if arm == "fibo" and (WORK / "results_fibo.jsonl").exists():
        for l in (WORK / "results_fibo.jsonl").read_text(encoding="utf-8").splitlines():
            r = json.loads(l)
            if r.get("phase") == "smoke":
                smoke = {"steps": r["steps"], "seconds": r["seconds"], "brief": r["brief"], "seed": r["seed"], "note": r.get("note")}
    warm = [r["exec_s"] for r in rows if not r["cold"]]
    cold = [r["exec_s"] for r in rows if r["cold"]]
    pk = [r["peak_mib"] for r in rows]
    return {"images": len(rows), "warm_median_s": round(statistics.median(warm), 2) if warm else None, "warm_min_s": min(warm) if warm else None,
            "warm_max_s": max(warm) if warm else None, "cold_first_s": cold, "total_s": round(sum(r["exec_s"] for r in rows), 1),
            "peak_mib_max": max(pk), "peak_gib_max": round(max(pk) / 1024, 2), "peak_mib_median": int(statistics.median(pk)), "peak_gib_median": round(statistics.median(pk) / 1024, 2),
            "smoke_50_steps": smoke, "steps": sorted({r.get("steps") for r in rows if r.get("steps")}) or [{"qwen21": 40, "qwena": 50, "klein": 16}.get(arm)]}


results = {"note": "extra arms (qwen21, fibo, qwena, klein); the MOSS-vs-Krea verdict of record is in results.json", "arms": {}, "per_image": []}
for arm in EXTRA:
    names = sorted(n for n, a in files.items() if a == arm)
    arm_res = {"images": len(names), "readers": {}}
    for r in READERS:
        have = [n for n in names if n in P[r]]
        if not have:
            continue
        pb = per_brief(P[r], [arm])
        # orig arms from the frozen results, same reader
        pbo = per_brief({k: v for k, v in P[r].items() if not k.startswith("__")}, ORIG_ARMS + [arm])
        arm_res["readers"][r] = {
            "pass": sum(P[r][n] for n in have), "n": len(have),
            "rerolls_total": sum(pb[b][arm]["rerolls"] for b in pb), "censored_briefs": sum(pb[b][arm]["censored"] for b in pb),
            "per_brief": {b: pb[b][arm] for b in pb},
            "rule_vs_krea-dense": compare(pbo, [arm], "krea-dense") if r != "rapid" or True else None,
            "rule_vs_moss-prompt": compare(pbo, [arm], "moss-prompt"),
            "rule_vs_best-of-MOSS_as_ref": None,
        }
        # the frozen reference "best of two MOSS arms per brief" is a max; here the extra arm is compared with that best by a manual loop
        rows, ge, rr_a, rr_m = [], 0, 0, 0
        for b in ALL_B:
            if b in pbo and arm in pbo[b] and "moss-prompt" in pbo[b]:
                ref_rate = max(pbo[b][a]["rate"] for a in ("moss-prompt", "moss-layout") if a in pbo[b])
                ref_rr = min(pbo[b][a]["rerolls"] for a in ("moss-prompt", "moss-layout") if a in pbo[b])
                ge += pbo[b][arm]["rate"] >= ref_rate
                rr_a += pbo[b][arm]["rerolls"]
                rr_m += ref_rr
                rows.append(b)
        arm_res["readers"][r]["rule_vs_best-of-MOSS_as_ref"] = {"n": len(rows), "arm_ge_ref_on": ge, "arm_rerolls": rr_a, "ref_rerolls": rr_m,
                                                                "rule_would_read": "PASS" if (len(rows) == 10 and ge >= 8 and rr_a < rr_m) else "FAIL"}
    arm_res["timing"] = timing(arm)
    results["arms"][arm] = arm_res
    for n in names:
        e = {"file": f"{arm}/{n}", "arm": arm, "brief": n.split("_")[0], "seed": int(n.rsplit("_", 1)[1][:3])}
        for r in READERS:
            if n in P[r]:
                e[r] = P[r][n]
            if n in T[r]:
                e[r + "_text"] = T[r][n]
        if n in notes:
            e["agent_note"] = notes[n]
        results["per_image"].append(e)
# agreement of each OCR reader with the agent visual reading, on the extra arms' images
agree = {}
for r in READERS[:-1]:
    for arm in EXTRA + ["ALL"]:
        names = [n for n, a in files.items() if (arm == "ALL" or a == arm) and n in P[r] and n in P["agent_read"]]
        if not names:
            continue
        tp = sum(P["agent_read"][n] and P[r][n] for n in names)
        fn = sum(P["agent_read"][n] and not P[r][n] for n in names)
        fp = sum((not P["agent_read"][n]) and P[r][n] for n in names)
        tn = sum((not P["agent_read"][n]) and (not P[r][n]) for n in names)
        agree.setdefault(r, {})[arm] = {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "agree": f"{tp + tn}/{len(names)}",
                                       "sens": round(tp / (tp + fn), 3) if tp + fn else None, "spec": round(tn / (tn + fp), 3) if tn + fp else None}
results["agreement_with_agent_reading"] = agree
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "results_extra.json").write_text(json.dumps(results, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

# ------------------------------------------------------------ tables
md = ["# Extra arms: tables (generated by scripts/score_extra.py)", ""]
for rd, label in (("unl_c2", "Unlimited-OCR c2 (reader of record, same as results_tables.md)"), ("agent_read", "AI reading (key agent_read; an AI model, not a person)"), ("unl_c0", "Unlimited-OCR c0"),
                  ("unl_c1", "Unlimited-OCR c1"), ("rapid", "RapidOCR")):
    cols = [a for a in EXTRA if rd in results["arms"][a]["readers"]]
    if not cols:
        continue
    md += [f"## Images passing out of 3 and rerolls, reader = {label}", "", "| brief | krea-dense | moss-prompt | moss-layout | " + " | ".join(cols) + " |", "|---|---|---|---|" + "---|" * len(cols)]
    pbo = per_brief(P[rd], ORIG_ARMS + EXTRA)
    for b in ALL_B:
        row = [b]
        for a in ["krea-dense", "moss-prompt", "moss-layout"] + cols:
            c = pbo.get(b, {}).get(a)
            row.append(f"{c['pass']}/{c['n']}, rr {c['rerolls']}{'*' if c['censored'] else ''}" if c else "n/a")
        md.append("| " + " | ".join(row) + " |")
    tot = ["total"]
    for a in ["krea-dense", "moss-prompt", "moss-layout"]:
        ok = [v for k, v in P[rd].items() if f"_{a}_" in k]
        tot.append(f"{sum(ok)}/{len(ok)}")
    for a in cols:
        x = results["arms"][a]["readers"][rd]
        tot.append(f"{x['pass']}/{x['n']}, rr {x['rerolls_total']}")
    md += ["| " + " | ".join(tot) + " |", ""]
md += ["## Frozen rule applied to the extra arms (information, NOT a verdict of record)", "",
       "| arm | reader | briefs >= krea-dense | rerolls arm / krea | reads | briefs >= moss-prompt | rerolls arm / moss-prompt | reads |", "|---|---|---|---|---|---|---|---|"]
for a in EXTRA:
    for rd, x in results["arms"][a]["readers"].items():
        k, m = x["rule_vs_krea-dense"], x["rule_vs_moss-prompt"]
        md.append(f"| {a} | {rd} | {k['arm_ge_ref_on']}/{k['n']} | {k['arm_rerolls']} / {k['ref_rerolls']} | {k['rule_would_read']} | {m['arm_ge_ref_on']}/{m['n']} | {m['arm_rerolls']} / {m['ref_rerolls']} | {m['rule_would_read']} |")
md += ["", "## Agreement of the OCR readers with the agent visual reading, extra-arm images (sens = agent-correct images the reader passes; spec = agent-wrong images it rejects)", "",
       "| reader | arm | agree | sens | spec |", "|---|---|---|---|---|"]
for rd, d_ in results["agreement_with_agent_reading"].items():
    for a, x in d_.items():
        md.append(f"| {rd} | {a} | {x['agree']} | {x['sens']} | {x['spec']} |")
md += ["", "## Time and VRAM (ComfyUI execution time for qwen21/qwena; wall time of the diffusers call for fibo; whole-card nvidia-smi peak)", "",
       "| arm | images | warm s/img median (min-max) | cold first s | peak MiB (GiB) max | peak MiB (GiB) median | total s | steps |", "|---|---|---|---|---|---|---|---|"]
for a in EXTRA:
    t = results["arms"][a]["timing"]
    if t:
        md.append(f"| {a} | {t['images']} | {t['warm_median_s']} ({t['warm_min_s']}-{t['warm_max_s']}) | {t['cold_first_s']} | {t['peak_mib_max']} ({t['peak_gib_max']}) | {t['peak_mib_median']} ({t['peak_gib_median']}) | {t['total_s']} | {t['steps']} |")
(OUT / "results_extra_tables.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print("\n".join(md))
