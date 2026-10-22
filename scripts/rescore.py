#!/usr/bin/env python3
"""Re-check the published numbers from the stored reader texts and logs. Needs no GPU, no images and no models: standard library only.

  python scripts/rescore.py

1. For every image of the label test (105 images of the four first arms, 120 of Qwen-Image-2.1, FIBO, Qwen-Image-2512 and Klein) and every OCR reader whose text is stored,
   apply scripts/scoring.py (the fixed scorer, see results/SCORER-FIX.md) to the stored text and compare with the stored PASS/FAIL.
2. Recompute, from those PASS/FAIL values, the per-arm totals, rerolls, the agreement of the reader of record with the AI reading, and the pre-registered criterion (best
   MOSS arm per brief against the Krea 2 dense-prompt arm: at least as good on >= 8 of 10 briefs AND fewer total rerolls) for every reader.
3. Recompute the battery-2 means (AI reading, p1-p8), the battery-3 passes (an image passes when every rubric item is P; the chalkboard OCR check is re-scored from its stored
   text) and the tally of the blind picks.
4. Recompute the seconds per image from the logs (results/logs/*.jsonl) and compare with the stored timing; print the FIBO speed comparison.
Prints what it found and exits 1 if anything does not match the stored values."""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scoring  # noqa: E402
from t004paths import OUT, PROMPTS  # noqa: E402

SEEDS = [101, 102, 103]
spec = json.loads((PROMPTS / "briefs.json").read_text(encoding="utf-8"))
STR = {b["id"]: b["strings"] for b in spec["briefs"]}
ALL_B = [b["id"] for b in spec["briefs"]]


def J(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


res, ext, b2, b3, vote = J("results.json"), J("results_extra.json"), J("results_battery2.json"), J("results_battery3.json"), J("blind_vote.json")
b3_spec = json.loads((PROMPTS / "battery3.json").read_text(encoding="utf-8"))
b3_reading = J("battery3_reading.json")
LOGS = OUT / "logs"
problems = []


def check(cond, what):
    if not cond:
        problems.append(what)


def jsonl(name):
    return [json.loads(l) for l in (LOGS / name).read_text(encoding="utf-8").splitlines() if l.strip()]


# ---- 1. stored texts -> PASS/FAIL
n_checked = 0
for e in res["per_image"] + ext["per_image"]:
    for reader in ("unl_c2", "unl_c0", "unl_c1", "rapid", "vlm"):
        if reader + "_text" in e and reader in e:
            n_checked += 1
            ok = scoring.check(e[reader + "_text"], STR[e["brief"]], True)[1]
            check(ok == e[reader], f"{e['file']} {reader}: recomputed {ok}, stored {e[reader]}")
    if "strict_L2_unl_c2" in e:
        n_checked += 1
        ok = scoring.check(e["unl_c2_text"], STR[e["brief"]], False)[1]
        check(ok == e["strict_L2_unl_c2"], f"{e['file']} strict: recomputed {ok}, stored {e['strict_L2_unl_c2']}")
print(f"1. {n_checked} reader results recomputed from the stored texts with the fixed scorer, {len(problems)} mismatches")

# ---- 2. totals, rerolls, agreement, criterion
rows = {}
for e in res["per_image"] + ext["per_image"]:
    rows[(e["brief"], e["arm"], e["seed"])] = e


def per_brief(reader, arm, brief):
    ok = [rows[(brief, arm, s)][reader] for s in SEEDS if (brief, arm, s) in rows and reader in rows[(brief, arm, s)]]
    if not ok:
        return None
    rr, cens = 0, True
    for x in ok:
        if x:
            cens = False
            break
        rr += 1
    return {"pass": sum(ok), "n": len(ok), "rate": sum(ok) / len(ok), "rerolls": rr, "censored": cens}


def criterion(reader, moss_arms, ref_arm):
    ge = mr = kr = n = 0
    for b in ALL_B:
        m = [per_brief(reader, a, b) for a in moss_arms]
        k = per_brief(reader, ref_arm, b)
        if k is None or not any(m):
            continue
        m = [x for x in m if x]
        n += 1
        ge += max(x["rate"] for x in m) >= k["rate"]
        mr += min(x["rerolls"] for x in m)
        kr += k["rerolls"]
    return {"n": n, "ge": ge, "moss_rerolls": mr, "ref_rerolls": kr, "verdict": "PASS" if (n == 10 and ge >= 8 and mr < kr) else "FAIL"}


ARMS7 = ("krea-dense", "krea-ie", "moss-prompt", "moss-layout", "qwen21", "fibo", "qwena", "klein")
print("\n2. label test: images passing (of 30, krea-ie of 15) and total rerolls per arm")
print(f"   {'arm':<12} {'reader of record (c2)':>24} {'AI reading':>16}")
for arm in ARMS7:
    cells = []
    for reader in ("unl_c2", "agent_read"):
        pbs = [per_brief(reader, arm, b) for b in ALL_B]
        pbs = [x for x in pbs if x]
        ps, n, rr = sum(x["pass"] for x in pbs), sum(x["n"] for x in pbs), sum(x["rerolls"] for x in pbs)
        cells.append(f"{ps}/{n}, rerolls {rr}")
        if arm in res["readers"][reader]["arm_totals"]:
            check(res["readers"][reader]["arm_totals"][arm]["pass"] == ps, f"{arm} {reader} total: recomputed {ps}")
        elif arm in ext["arms"] and reader in ext["arms"][arm]["readers"]:
            x = ext["arms"][arm]["readers"][reader]
            check((x["pass"], x["rerolls_total"]) == (ps, rr), f"{arm} {reader}: recomputed {ps}/{rr}, stored {x['pass']}/{x['rerolls_total']}")
    print(f"   {arm:<12} {cells[0]:>24} {cells[1]:>16}")

print("\n   agreement of the reader of record (c2) with the AI reading, images where both say pass or both say fail")
groups = {"four first arms": ("krea-dense", "krea-ie", "moss-prompt", "moss-layout"), "Qwen-Image-2.1 + FIBO + Qwen-Image-2512": ("qwen21", "fibo", "qwena"), "Klein": ("klein",)}
tot = [0, 0]
for label, arms in groups.items():
    imgs = [e for e in res["per_image"] + ext["per_image"] if e["arm"] in arms]
    agree = sum(e["unl_c2"] == e["agent_read"] for e in imgs)
    tot[0] += agree
    tot[1] += len(imgs)
    print(f"   {label:<42} {agree}/{len(imgs)}")
    if label == "four first arms":
        check(res["agreement_with_agent_reading_on_test_images"]["unl_c2"]["agree"] == f"{agree}/{len(imgs)}", "agreement, four first arms")
    else:
        for a in arms:
            ia = [e for e in imgs if e["arm"] == a]
            check(ext["agreement_with_agent_reading"]["unl_c2"][a]["agree"] == f"{sum(e['unl_c2'] == e['agent_read'] for e in ia)}/{len(ia)}", f"agreement {a}")
print(f"   {'all':<42} {tot[0]}/{tot[1]}")

print("\n   pre-registered criterion (best MOSS arm per brief vs Krea 2 dense prompt; needs >= 8 of 10 briefs and fewer rerolls):")
for reader in ("unl_c2", "unl_c0", "unl_c1", "rapid", "vlm", "agent_read"):
    c = criterion(reader, ["moss-prompt", "moss-layout"], "krea-dense")
    st = res["readers"][reader]["comparisons"]["HEADLINE best-of-MOSS vs krea-dense"]
    check((c["ge"], c["moss_rerolls"], c["ref_rerolls"], c["verdict"]) == (st["moss_ge_ref_on"], st["moss_rerolls"], st["ref_rerolls"], st["verdict"]), f"criterion {reader}")
    tag = "  <- reader of record" if reader == "unl_c2" else ""
    print(f"   {reader:<11} MOSS >= Krea on {c['ge']}/10 briefs, rerolls MOSS {c['moss_rerolls']} vs Krea {c['ref_rerolls']}: {'MET' if c['verdict'] == 'PASS' else 'NOT MET'}{tag}")
rec = criterion("unl_c2", ["moss-prompt", "moss-layout"], "krea-dense")
check((rec["ge"], rec["moss_rerolls"], rec["ref_rerolls"], rec["verdict"]) == (8, 15, 16, "PASS"), "verdict of record is not 8/10, 15 vs 16, met")

# ---- 3. battery 2, battery 3, blind vote
print("\n3. battery 2, mean of the AI reading over p1-p8 (realism, anatomy, composition, slop-free; overall = mean of the four)")
P8 = [p["id"] for p in json.loads((PROMPTS / "battery2.json").read_text(encoding="utf-8"))["prompts"]]
for arm, a in b2["arms"].items():
    keys = [k for k in b2["reading"] if f"_{arm}_" in k and k.split("_")[0] in P8]
    means = {c: round(statistics.mean(b2["reading"][k][c] for k in keys), 2) for c in ("realism", "anatomy", "composition", "slop_free")}
    overall = round(statistics.mean(statistics.mean(b2["reading"][k][c] for c in means) for k in keys), 2)
    check(means == a["mean"] and overall == a["overall"], f"battery2 means for {arm}")
    print(f"   {arm:<11} {len(keys):>2} images  {means}  overall {overall}")

print("\n   battery 3, hard prompts: images passing out of 12 (an image passes when every rubric item is P)")
items_n = {p["id"]: len(p["rubric"]) for p in b3_spec["prompts"]}
per_arm = {}
for e in b3["per_image"]:
    rd = b3_reading[f"{e['prompt']}|{e['arm']}|{e['seed']}"]
    check(len(rd["items"]) == items_n[e["prompt"]], f"battery3 rubric length {e['prompt']}")
    p = all(c == "P" for c in rd["items"])
    check(p == e["pass"] and [c == "P" for c in rd["items"]] == list(e["items"].values()), f"battery3 pass {e['prompt']} {e['arm']} {e['seed']}")
    if e["prompt"].startswith("h4"):
        ok = scoring.check(e["ocr_c2_text"], [{"s": "FRESH BREAD DAILY 7AM-2PM", "min_count": 1}], True)[1]
        check(ok == e["ocr_c2_pass"], f"battery3 h4 OCR {e['arm']} {e['seed']}")
        old = "FRESHBREADDAILY7AM2PM" in "".join(c for c in e["ocr_c2_text"].upper() if c.isalnum())
        check(old == e["ocr_c2_pass_pre_fix"], f"battery3 h4 OCR old rule {e['arm']} {e['seed']}")
    per_arm.setdefault(e["arm"], {}).setdefault(e["prompt"], []).append(p)
for arm, d in per_arm.items():
    n, ok = sum(len(v) for v in d.values()), sum(sum(v) for v in d.values())
    check(b3["summary"][arm]["passes"] == ok and b3["summary"][arm]["n"] == n, f"battery3 summary {arm}")
    print(f"   {arm:<11} {ok:>2}/{n}   " + "  ".join(f"{p.split('-')[0]} {sum(v)}/{len(v)}" for p, v in d.items()))

tally = {}
for p in vote["picks"]:
    for m in p["models"]:
        tally[m] = tally.get(m, 0) + 1 / len(p["models"])
check({k: round(v, 2) for k, v in tally.items()} == vote["tally"], "blind vote tally")
six = {m: round(tally.get(m, 0), 2) for m in ("qwen21", "krea-dense", "fibo", "qwena", "moss-prompt", "klein")}
check(six == {k: round(v, 2) for k, v in vote["tally_six_models"].items()}, "blind vote tally, six models")
print("\n   blind picks (9 prompts, one vote each, a two-letter answer counts half each; the same nine picks stood in the six-model round):",
      {k: v for k, v in sorted(six.items(), key=lambda x: -x[1])})

# ---- 4. seconds per image from the logs
print("\n4. warm median seconds per image, recomputed from the logs (first image of a run is cold and left out)")


def warm_median(rows_, nd):
    w = [r["exec_s"] for r in rows_ if not r.get("cold")]
    return round(statistics.median(w), nd) if w else None


gen = [r for r in jsonl("results_gen.jsonl") if r.get("phase") == "test" and r.get("ok")]
extra = [r for r in jsonl("results_extra.jsonl") if r.get("phase") == "test" and r.get("ok")]
fibo = [r for r in jsonl("results_fibo.jsonl") if r.get("phase") == "test" and r.get("ok")]
bat2 = [r for r in jsonl("results_battery2.jsonl") if r.get("phase") == "b2" and r.get("ok")]
bat3 = {}
for r in jsonl("results_battery3.jsonl"):
    if r.get("phase") == "b3" and r.get("ok"):
        bat3[(r["brief"], r["arm"], r["seed"])] = r
print(f"   {'model':<12} {'label run':>10} {'beyond labels':>14} {'hard prompts':>13}")
for arm in ("krea-dense", "krea-ie", "moss-prompt", "moss-layout", "qwen21", "fibo", "qwena", "klein"):
    if arm in res["timing"]:
        m1 = warm_median([r for r in gen if r["arm"] == arm], 1)
        check(m1 == res["timing"][arm]["warm_median_s"], f"timing label run {arm}")
    elif arm == "fibo":
        m1 = warm_median([dict(exec_s=r["exec_s"], cold=r.get("cold")) for r in fibo], 2)
        check(m1 == ext["arms"]["fibo"]["timing"]["warm_median_s"], "timing label run fibo")
    else:
        m1 = warm_median([r for r in extra if r["arm"] == arm], 2)
        check(m1 == ext["arms"][arm]["timing"]["warm_median_s"], f"timing label run {arm}")
    m2 = warm_median([r for r in bat2 if r["arm"] == arm and r["brief"] in P8], 2) if arm in b2["arms"] else None
    if m2 is not None:
        check(m2 == b2["arms"][arm]["timing"]["warm_median_s"], f"timing battery 2 {arm}")
    secs = [r["exec_s"] for (p, a, s), r in bat3.items() if a == arm and not r.get("cold")]
    m3 = round(statistics.median(secs), 1) if secs else None
    if arm in b3["summary"]:
        check(m3 == b3["summary"][arm]["median_warm_s"], f"timing battery 3 {arm}")
    print(f"   {arm:<12} {m1 if m1 is not None else '-':>10} {m2 if m2 is not None else '-':>14} {m3 if m3 is not None else '-':>13}")

print("\n   FIBO 2.0-dev: native ComfyUI against diffusers (30 steps; s/img, whole-card peak GiB; the first image of each run includes loading)")
native = jsonl("results_fibo_comfy.jsonl")
dif = {"b07-endcard-hoodie": [r for r in fibo if r["brief"] == "b07-endcard-hoodie" and r["seed"] == 101][-1],
       "p6-night-rain": [r for r in bat2 if r["arm"] == "fibo" and r["brief"] == "p6-night-rain" and r["seed"] == 101][-1]}
for r in native:
    print(f"   native {r['arm'].replace('fibo-comfy-', ''):<13} {r['brief']:<20} {r['exec_s']:>6} s  {r['peak_mib'] / 1024:5.1f} GiB  {'(cold)' if r['cold'] else '(warm)'}")
for k, r in dif.items():
    print(f"   diffusers bf16      {k:<20} {r['exec_s']:>6} s  {r.get('card_peak_mib', r.get('peak_mib')) / 1024:5.1f} GiB")

if problems:
    print(f"\nMISMATCH ({len(problems)}):")
    for p in problems[:20]:
        print("  ", p)
    sys.exit(1)
print("\nOK: every recomputed number equals the stored one.")
