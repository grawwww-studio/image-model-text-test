#!/usr/bin/env python3
"""Final scoring of the label test (CPU, standard library): every reader on the 105 test images, the pre-registered criterion for each reader, reader validity on the controls,
agreement with the AI reading. Reads the raw reader output and logs from WORK (see t004paths.py), writes results.json and results_tables.md to OUT.
Rules: results/PREREG.md (with Addendum 1), matching: scripts/scoring.py.
Readers: unl_c2 (THE FROZEN GATE: Unlimited-OCR, config chosen on controls only), unl_c0, unl_c1, unl_any (post-hoc union of the three, reported as such), rapid, vlm, agent_read (the agent visual reading).
Sensitivity runs: the headline when the disputed agent visual readings are resolved against MOSS."""
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import scoring  # noqa: E402
from t004paths import OUT, PROMPTS, WORK  # noqa: E402

ARMS = ["krea-dense", "krea-ie", "moss-prompt", "moss-layout"]
SEEDS = [101, 102, 103]
spec = json.loads((PROMPTS / "briefs.json").read_text(encoding="utf-8"))
BR = {b["id"]: b for b in spec["briefs"]}
IE_B = [b["id"] for b in spec["briefs"] if b["ie"]]
ALL_B = [b["id"] for b in spec["briefs"]]


def J(p):
    return json.loads((p if isinstance(p, Path) else WORK / p).read_text(encoding="utf-8"))


unl = {c: J(f"ocr/test_unl_{c}.json")["items"] for c in ("c0", "c1", "c2")}
rapid = J("ocr/rapid_test.json")["items"]
vlm = J("ocr/test_vlm.json")["items"]
agent_rd = J("ocr/agent_reading.json")
gen = {}
for line in (WORK / "results_gen.jsonl").read_text(encoding="utf-8").splitlines():
    r = json.loads(line)
    if r.get("phase") == "test":
        gen[(r["arm"], r["brief"], r["seed"])] = r


def ocr_pass(items, name):
    return scoring.check(items[name]["text"], BR[name.split("_")[0]]["strings"], True)[1]


def strict_pass(items, name):
    return scoring.check(items[name]["text"], BR[name.split("_")[0]]["strings"], False)[1]


images = []
for b in ALL_B:
    for arm in ARMS:
        if arm == "krea-ie" and not BR[b]["ie"]:
            continue
        for s in SEEDS:
            images.append((b, arm, s, f"{b}_{arm}_{s}.png"))

READERS = ["unl_c2", "unl_c0", "unl_c1", "unl_any", "rapid", "vlm", "agent_read"]
P = {r: {} for r in READERS}
for b, arm, s, n in images:
    P["unl_c0"][n] = ocr_pass(unl["c0"], n)
    P["unl_c1"][n] = ocr_pass(unl["c1"], n)
    P["unl_c2"][n] = ocr_pass(unl["c2"], n)
    P["unl_any"][n] = P["unl_c0"][n] or P["unl_c1"][n] or P["unl_c2"][n]
    P["rapid"][n] = ocr_pass(rapid, n)
    P["vlm"][n] = ocr_pass(vlm, n)
    P["agent_read"][n] = agent_rd[n]["pass"]


def per_brief(reader, passmap):
    out = {}
    for b in ALL_B:
        for arm in ARMS:
            rows = [passmap[f"{b}_{arm}_{s}.png"] for s in SEEDS if f"{b}_{arm}_{s}.png" in passmap]
            if not rows:
                continue
            rr, cens = 0, True
            for ok in rows:
                if ok:
                    cens = False
                    break
                rr += 1
            out.setdefault(b, {})[arm] = {"pass": sum(rows), "n": len(rows), "rate": sum(rows) / len(rows), "rerolls": rr, "censored": cens}
    return out


def compare(pb, moss_arms, ref_arm, briefs):
    rows, mr, kr, ok_n = [], 0, 0, 0
    for b in briefs:
        if ref_arm not in pb.get(b, {}):
            continue
        m_rate = max(pb[b][a]["rate"] for a in moss_arms if a in pb[b])
        m_rr = min(pb[b][a]["rerolls"] for a in moss_arms if a in pb[b])
        k = pb[b][ref_arm]
        ge = m_rate >= k["rate"]
        ok_n += ge
        mr += m_rr
        kr += k["rerolls"]
        rows.append({"brief": b, "moss_rate": round(m_rate, 2), "ref_rate": round(k["rate"], 2), "moss_ge_ref": ge, "moss_rerolls": m_rr, "ref_rerolls": k["rerolls"]})
    return {"moss_arms": moss_arms, "ref_arm": ref_arm, "n": len(rows), "moss_ge_ref_on": ok_n, "moss_rerolls": mr, "ref_rerolls": kr, "rows": rows,
            "rate_ok": ok_n >= 8 and len(rows) == 10, "rerolls_ok": mr < kr,
            "verdict": ("PASS" if (ok_n >= 8 and len(rows) == 10 and mr < kr) else "FAIL") if len(rows) == 10 else "n/a (5 briefs)"}


results = {"readers": {}}
for r in READERS:
    pb = per_brief(r, P[r])
    comps = {
        "HEADLINE best-of-MOSS vs krea-dense": compare(pb, ["moss-prompt", "moss-layout"], "krea-dense", ALL_B),
        "moss-prompt vs krea-dense": compare(pb, ["moss-prompt"], "krea-dense", ALL_B),
        "moss-layout vs krea-dense": compare(pb, ["moss-layout"], "krea-dense", ALL_B),
        "best-of-MOSS vs krea-ie (b01-b05)": compare(pb, ["moss-prompt", "moss-layout"], "krea-ie", IE_B),
    }
    arm_tot = {}
    for arm in ARMS:
        names = [n for b, a, s, n in images if a == arm]
        arm_tot[arm] = {"images": len(names), "pass": sum(P[r][n] for n in names)}
    results["readers"][r] = {"per_brief": pb, "comparisons": comps, "arm_totals": arm_tot}

# agreement with agent visual reading on the test images
agree = {}
for r in READERS[:-1]:
    tp = fp = fn = tn = 0
    for _, _, _, n in images:
        h, g = P["agent_read"][n], P[r][n]
        tp += h and g
        fn += h and not g
        fp += (not h) and g
        tn += (not h) and (not g)
    agree[r] = {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "sens": round(tp / (tp + fn), 3), "spec": round(tn / (tn + fp), 3), "agree": f"{tp + tn}/{tp + tn + fp + fn}"}
results["agreement_with_agent_reading_on_test_images"] = agree

# reader validity on the controls (the pre-declared rule: sens >= 0.80 and spec >= 0.90)


def ctrl_eval(spec_file, ocr_file, fold=True):
    sp = {r["file"]: r for r in J(spec_file)}
    oc = J(ocr_file)["items"]
    tp = fn = tn = fp = 0
    for f, r in sp.items():
        if f not in oc:
            continue
        truth = r.get("truth_pass", r.get("kind") == "pos")
        ok = scoring.check(oc[f]["text"], r["expected"], fold)[1]
        tp += truth and ok
        fn += truth and not ok
        tn += (not truth) and (not ok)
        fp += (not truth) and ok
    return tp, fn, tn, fp


validity = {}
for name, files in {"unl_c0": ("ocr/controls_unl_c0.json", "ocr/controlsreal_unl_c0.json"), "unl_c1": ("ocr/controls_unl_c1.json", "ocr/controlsreal_unl_c1.json"),
                    "unl_c2": ("ocr/controls_unl_c2.json", "ocr/controlsreal_unl_c2.json"), "vlm": ("ocr/controls_vlm.json", "ocr/controlsreal_vlm.json"),
                    "rapid": ("ocr/controls_rapid.json", "ocr/controlsreal_rapid.json")}.items():
    a = ctrl_eval(PROMPTS / "controls.json", files[0])
    b = ctrl_eval(PROMPTS / "controls_real.json", files[1]) if (WORK / files[1]).exists() else (0, 0, 0, 0)
    t = tuple(x + y for x, y in zip(a, b))
    sens, spec_ = t[0] / (t[0] + t[1]), t[2] / (t[2] + t[3])
    validity[name] = {"rendered+pack": {"tp": a[0], "fn": a[1], "tn": a[2], "fp": a[3]}, "realistic": {"tp": b[0], "fn": b[1], "tn": b[2], "fp": b[3]},
                      "sens": round(sens, 3), "spec": round(spec_, 3), "valid_by_rule": sens >= 0.8 and spec_ >= 0.9}
results["controls_validity"] = validity

# sensitivity of the agent-read headline to the disputed readings
sens_runs = {}
for label, flips in {
    "as read": {},
    "disputed Krea b02 102+103 failed (favours MOSS)": {"b02-hoodie-chest_krea-dense_102.png": False, "b02-hoodie-chest_krea-dense_103.png": False},
    "disputed MOSS-prompt b02 103 failed (hurts MOSS)": {"b02-hoodie-chest_moss-prompt_103.png": False},
}.items():
    pm = dict(P["agent_read"])
    pm.update(flips)
    pb = per_brief("agent_read", pm)
    sens_runs[label] = {k: compare(pb, a, "krea-dense", ALL_B) for k, a in {"best-of-MOSS": ["moss-prompt", "moss-layout"], "moss-prompt": ["moss-prompt"]}.items()}
    sens_runs[label] = {k: {"moss_ge_ref_on": v["moss_ge_ref_on"], "moss_rerolls": v["moss_rerolls"], "ref_rerolls": v["ref_rerolls"], "verdict": v["verdict"]} for k, v in sens_runs[label].items()}
results["agent_reading_headline_sensitivity"] = sens_runs

# timing and VRAM per arm (from results_gen.jsonl)
timing = {}
for arm in ARMS:
    rows = [r for (a, b, s), r in gen.items() if a == arm]
    warm = [r["exec_s"] for r in rows if not r["cold"]]
    cold = [r["exec_s"] for r in rows if r["cold"]]
    timing[arm] = {"images": len(rows), "failed": sum(1 for r in rows if not r["ok"]), "warm_median_s": round(statistics.median(warm), 1), "warm_min_s": min(warm), "warm_max_s": max(warm),
                   "cold_s": cold, "peak_mib_max": max(r["peak_mib"] for r in rows), "peak_mib_median": int(statistics.median([r["peak_mib"] for r in rows])), "total_exec_s": round(sum(r["exec_s"] for r in rows), 1)}
results["timing"] = timing
results["per_image"] = [{"file": n, "brief": b, "arm": a, "seed": s, **{r: P[r][n] for r in READERS}, "agent_note": agent_rd[n]["note"],
                         "strict_L2_unl_c2": strict_pass(unl["c2"], n), "exec_s": gen[(a, b, s)]["exec_s"], "peak_mib": gen[(a, b, s)]["peak_mib"],
                         "unl_c2_text": unl["c2"][n]["text"], "unl_c0_text": unl["c0"][n]["text"], "rapid_text": rapid[n]["text"], "vlm_text": vlm[n]["text"]} for b, a, s, n in images]
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

# tables
L = []
for r in ("agent_read", "unl_c2"):
    pb = results["readers"][r]["per_brief"]
    L.append(f"### Per brief: images passing (of 3), rerolls before the first pass (* = no pass in 3 seeds), reader = {r}")
    L.append("| brief | " + " | ".join(ARMS) + " |")
    L.append("|---|" + "---|" * len(ARMS))
    for b in ALL_B:
        cells = []
        for a in ARMS:
            x = pb.get(b, {}).get(a)
            cells.append("n/a" if x is None else f"{x['pass']}/3, rr {x['rerolls']}{'*' if x['censored'] else ''}")
        L.append(f"| {b} | " + " | ".join(cells) + " |")
    L.append("| total | " + " | ".join(f"{results['readers'][r]['arm_totals'][a]['pass']}/{results['readers'][r]['arm_totals'][a]['images']}" for a in ARMS) + " |")
    L.append("")
L.append("### Frozen criterion by reader (best-of-MOSS vs krea-dense, then each arm alone, then vs krea-ie)")
L.append("| reader | headline: briefs MOSS >= Krea | rerolls MOSS / Krea | headline verdict | moss-prompt alone | moss-layout alone | best-of-MOSS vs krea-ie (b01-b05) |")
L.append("|---|---|---|---|---|---|---|")
for r in READERS:
    c = results["readers"][r]["comparisons"]
    h, mp, ml, ie = c["HEADLINE best-of-MOSS vs krea-dense"], c["moss-prompt vs krea-dense"], c["moss-layout vs krea-dense"], c["best-of-MOSS vs krea-ie (b01-b05)"]
    L.append(f"| {r} | {h['moss_ge_ref_on']}/10 | {h['moss_rerolls']} / {h['ref_rerolls']} | {h['verdict']} | {mp['moss_ge_ref_on']}/10, rr {mp['moss_rerolls']} vs {mp['ref_rerolls']}: {mp['verdict']} | "
             f"{ml['moss_ge_ref_on']}/10, rr {ml['moss_rerolls']} vs {ml['ref_rerolls']}: {ml['verdict']} | {ie['moss_ge_ref_on']}/5 |")
L.append("")
L.append("### Agreement of each reader with agent visual reading, on the 105 test images")
L.append("| reader | images the agent read as correct that the reader passes (sens) | images the agent read as wrong that the reader rejects (spec) | agree |")
L.append("|---|---|---|---|")
for r, a in agree.items():
    L.append(f"| {r} | {a['tp']}/{a['tp'] + a['fn']} = {a['sens']} | {a['tn']}/{a['tn'] + a['fp']} = {a['spec']} | {a['agree']} |")
L.append("")
L.append("### Reader validity on the controls (pre-declared rule: sens >= 0.80 and spec >= 0.90)")
L.append("| reader | rendered + pack shots (tp/fn, tn/fp) | realistic generated (tp/fn, tn/fp) | sens | spec | valid |")
L.append("|---|---|---|---|---|---|")
for r, v in validity.items():
    a, b = v["rendered+pack"], v["realistic"]
    L.append(f"| {r} | {a['tp']}/{a['fn']}, {a['tn']}/{a['fp']} | {b['tp']}/{b['fn']}, {b['tn']}/{b['fp']} | {v['sens']} | {v['spec']} | {'yes' if v['valid_by_rule'] else 'NO'} |")
L.append("")
L.append("### Time and VRAM per arm (ComfyUI execution time; whole-card nvidia-smi peak)")
L.append("| arm | images | warm s/img median (min-max) | cold first image s | peak MiB max / median | total s |")
L.append("|---|---|---|---|---|---|")
for a, t in timing.items():
    L.append(f"| {a} | {t['images']} | {t['warm_median_s']} ({t['warm_min_s']}-{t['warm_max_s']}) | {t['cold_s']} | {t['peak_mib_max']} / {t['peak_mib_median']} | {t['total_exec_s']} |")
(OUT / "results_tables.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L))
print(json.dumps(sens_runs, indent=1))
