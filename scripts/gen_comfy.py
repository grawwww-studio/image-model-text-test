#!/usr/bin/env python3
"""Generation runner for the six ComfyUI arms: builds each arm's graph (API format), queues it on a running ComfyUI server over HTTP, saves the images
and logs one line per image (execution time from ComfyUI's own timestamps, whole-card VRAM peak from nvidia-smi). Resumable. Standard library only.

  gen_comfy.py dump DIR                       write the API-format graph of each arm (brief b03, seed 101) to DIR: the files in workflows/comfyui/
  gen_comfy.py labels ARM [ARM ...]           the label test: 10 briefs x 3 seeds, 1024x1792 (prompts/briefs.json)
  gen_comfy.py battery2 SEEDS ARM [ARM ...]   the "beyond labels" prompts, e.g. battery2 101,102 krea-dense moss-prompt qwen21 qwena klein
                                              (BATTERY_SPEC=prompts/battery2_p9.json runs the extra prompt p9 instead)
  gen_comfy.py battery3 SEEDS ARM [ARM ...]   the hard prompts (prompts/battery3.json), same arms as battery2
  gen_comfy.py free                           ask ComfyUI to unload its models (so a script that needs the card can have it)

Arms: krea-dense, krea-ie, moss-prompt, moss-layout, qwen21, qwena, klein. FIBO runs through diffusers (fibo_labels.py, fibo_battery2.py, fibo_battery3.py) or, in ComfyUI builds that
contain its native nodes, through fibo_comfy_run.py.
krea-ie needs the reference pack shots named in prompts/briefs.json (field ie.ref, briefs b01-b05); they are not in this repository: put your own images
in --packs DIR (default WORK/packs). Briefs b06-b10 have no pack shot: that arm is simply not run for them.
klein needs files under the names in g_klein() below (see the README: the encoder is the two official shards merged by merge_safetensors_shards.py).

Environment: COMFY_URL (default http://localhost:8188), T004_WORK (see t004paths.py), T004_VRAM=0 to skip the nvidia-smi sampling.
Images: WORK/images/<brief>_<arm>_<seed>.png (the four first arms), WORK/images/<arm>/... (qwen21, qwena, klein), WORK/images/battery2/<arm>/<prompt>_<arm>_<seed>.png, WORK/images/battery3/<arm>/...
Logs:   WORK/results_gen.jsonl (first four arms), results_extra.jsonl (qwen21, qwena, klein), results_battery2.jsonl, results_battery3.jsonl.
Settings are the ones used in the test: see the README and prompts/battery2.json ("settings")."""
import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t004paths import PROMPTS, WORK  # noqa: E402

COMFY = os.environ.get("COMFY_URL", "http://localhost:8188").rstrip("/")
W, H = 1024, 1792
FROZEN_ARMS = ["krea-dense", "krea-ie", "moss-prompt", "moss-layout"]
EXTRA_ARMS = ["qwen21", "qwena", "klein"]
ALL_ARMS = FROZEN_ARMS + EXTRA_ARMS

NEG_MOSS = "nsfw, worst quality, bad anatomy, watermark, jpeg artifact"   # vendor-recommended (user guide, template)
MOSS_OFFICIAL = dict(steps=50, cfg=3.0, sampler="euler", scheduler="simple", slg_end=1.0)    # OpenMOSS README defaults: what the test used
Q21_STEPS, Q21_CFG = 40, 1.0
QA_STEPS, QA_CFG, QA_SHIFT = 50, 4.0, 3.1
KLEIN_UNET, KLEIN_TE, KLEIN_VAE, KLEIN_STEPS, KLEIN_CFG = "flux3-image-klein-bf16.safetensors", "qwen3vl_4b_instruct_bf16_bfl-merged.safetensors", "flux2-vae.safetensors", 16, 1.0
QA_NEG = "低分辨率，低画质，肢体畸形，手指畸形，画面过饱和，蜡像感，人脸无细节，过度光滑，画面具有AI感。构图混乱。文字模糊，扭曲"   # template + model card verbatim


# ------------------------------------------------------------------ graphs (API format)
def g_krea_dense(prompt, seed, prefix, w=W, h=H):
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "krea2_turbo_fp8_scaled.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3vl_4b_fp8_scaled.safetensors", "type": "krea2", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
        "7": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["6", 0]}},
        "8": {"class_type": "EmptySD3LatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "9": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["8", 0],
              "seed": seed, "steps": 9, "cfg": 1.0, "sampler_name": "er_sde", "scheduler": "beta", "denoise": 1.0}},
        "10": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["3", 0]}},
        "11": {"class_type": "SaveImage", "inputs": {"images": ["10", 0], "filename_prefix": prefix}},
    }


def g_krea_ie(prompt, ref_name, seed, prefix, w=W, h=H, boost=4.0, grounding=768):
    """Krea 2 Turbo + Identity Edit v1.2 (a Krea 2 derivative, needs the ComfyUI-Krea2Edit nodes), one reference image (the pack shot)."""
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "krea2_turbo_fp8_scaled.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3vl_4b_fp8_scaled.safetensors", "type": "krea2", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
        "4": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": "Krea2/krea2_identity_edit_v1_2.safetensors", "strength_model": 1.0}},
        "20": {"class_type": "LoadImage", "inputs": {"image": ref_name}},
        "21": {"class_type": "VAEEncode", "inputs": {"pixels": ["20", 0], "vae": ["3", 0]}},
        "7": {"class_type": "EmptySD3LatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "30": {"class_type": "Krea2EditModelPatch", "inputs": {"model": ["4", 0], "source_latent": ["21", 0], "vae": ["3", 0], "source_image": ["20", 0],
               "target_latent": ["7", 0], "ref_boost": boost, "fit_mode": "fit"}},
        "5": {"class_type": "Krea2EditGroundedEncode", "inputs": {"clip": ["2", 0], "prompt": prompt, "image": ["20", 0], "grounding_px": grounding}},
        "6": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["5", 0]}},
        "8": {"class_type": "KSampler", "inputs": {"model": ["30", 0], "positive": ["5", 0], "negative": ["6", 0], "latent_image": ["7", 0], "seed": seed,
              "steps": 10, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["3", 0]}},
        "10": {"class_type": "SaveImage", "inputs": {"images": ["9", 0], "filename_prefix": prefix}},
    }


def g_moss(text, seed, prefix, w=W, h=H, cfgset=MOSS_OFFICIAL, neg=NEG_MOSS):
    """MOSS-Image SFT int8 + Qwen3.5-9B int8 encoder (CLIPLoader type moss_image) + FLUX.2 small decoder.
    `text` is either the plain prompt or the layout JSON string; the prompt upsampler is OFF (the raw text goes to the encoder)."""
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "moss_image_sft_int8_convrot.safetensors", "weight_dtype": "default"}},
        "15": {"class_type": "SkipLayerGuidanceDiTSimple", "inputs": {"model": ["1", 0], "double_layers": "", "single_layers": "22", "start_percent": 0.0, "end_percent": cfgset["slg_end"]}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3.5_9b_int8_convrot.safetensors", "type": "moss_image", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "flux2-vae_small.safetensors"}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": text, "clip": ["2", 0]}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": neg, "clip": ["2", 0]}},
        "6": {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "7": {"class_type": "KSampler", "inputs": {"model": ["15", 0], "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["6", 0], "seed": seed,
              "steps": cfgset["steps"], "cfg": cfgset["cfg"], "sampler_name": cfgset["sampler"], "scheduler": cfgset["scheduler"], "denoise": 1.0}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": prefix}},
    }


def g_qwen21(prompt, seed, prefix, w=W, h=H, steps=Q21_STEPS):
    """Qwen-Image-2.1 (Qwen Research License: research or evaluation only). Graph of the ComfyUI template image_qwen_image_2_1_t2i; prompt enhancer off."""
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "qwen_image_2.1_int8_convrot.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "QwenImage21Cache", "inputs": {"model": ["1", 0], "device": "auto", "dtype": "default"}},
        "3": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3vl_8b_int8_convrot.safetensors", "type": "qwen_image", "device": "default"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_2.1_vae_bf16.safetensors"}},
        "5": {"class_type": "TextEncodeQwenImage21", "inputs": {"clip": ["3", 0], "prompt": prompt, "negative_prompt": "", "resolution": 1024}},
        "6": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "7": {"class_type": "KSampler", "inputs": {"model": ["2", 0], "positive": ["5", 0], "negative": ["5", 1], "latent_image": ["6", 0], "seed": seed,
              "steps": steps, "cfg": Q21_CFG, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["4", 0]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": prefix}},
    }


def g_qwena(prompt, seed, prefix, w=W, h=H):
    """Qwen-Image-2512 fp8 (tagged Apache-2.0). Graph of the ComfyUI template image_qwen_Image_2512."""
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "qwen_image_2512_fp8_e4m3fn.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": QA_SHIFT}},
        "3": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors", "type": "qwen_image", "device": "default"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["3", 0]}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": QA_NEG, "clip": ["3", 0]}},
        "7": {"class_type": "EmptySD3LatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "8": {"class_type": "KSampler", "inputs": {"model": ["2", 0], "positive": ["5", 0], "negative": ["6", 0], "latent_image": ["7", 0], "seed": seed,
              "steps": QA_STEPS, "cfg": QA_CFG, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["4", 0]}},
        "10": {"class_type": "SaveImage", "inputs": {"images": ["9", 0], "filename_prefix": prefix}},
    }


def g_klein(prompt, seed, prefix, w=W, h=H, steps=KLEIN_STEPS):
    """FLUX 3 Image Klein (Black Forest Labs, distilled, bf16; FLUX Kommunity License v.1.0). ComfyUI core nodes only. Graph of the ComfyUI template image_flux3_klein_distilled_t2i
    without its prompt-upsampler branch: the prompt upsampler is OFF (our prompts are already full scene captions). 16 steps, euler/simple, cfg 1: the card's defaults."""
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": KLEIN_UNET, "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": KLEIN_TE, "type": "flux3", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": KLEIN_VAE}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["2", 0]}},
        "6": {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "7": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["6", 0], "seed": seed,
              "steps": steps, "cfg": KLEIN_CFG, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": prefix}},
    }


def pack_name(brief):
    return "t004_pack_" + brief["id"].split("-")[0] + ".png"          # the name the reference gets inside ComfyUI's input folder


def build_label(arm, brief, seed, w=W, h=H):
    prefix = f"{'t004' if arm in FROZEN_ARMS else 't004x'}/{brief['id']}_{arm}_{seed}"      # output prefix inside ComfyUI (t004 = our number for this test)
    if arm == "krea-dense":
        return g_krea_dense(brief["prompt"], seed, prefix, w, h)
    if arm == "krea-ie":
        return g_krea_ie(brief["ie_prompt"], pack_name(brief), seed, prefix, w, h)
    if arm == "moss-prompt":
        return g_moss(brief["prompt"], seed, prefix, w, h)
    if arm == "moss-layout":
        return g_moss(brief["layout_json"], seed, prefix, w, h)
    if arm == "qwen21":
        return g_qwen21(brief["prompt"], seed, prefix, w, h)
    if arm == "qwena":
        return g_qwena(brief["prompt"], seed, prefix, w, h)
    if arm == "klein":
        return g_klein(brief["prompt"], seed, prefix, w, h)
    raise SystemExit(f"unknown arm {arm}; arms: {', '.join(ALL_ARMS)}")


def build_battery(arm, p, seed, prefix):
    w, h = p["canvas"]
    if arm == "krea-dense":
        return g_krea_dense(p["prompt"], seed, prefix, w, h)
    if arm == "moss-prompt":
        return g_moss(p["prompt"], seed, prefix, w, h)
    if arm == "qwen21":
        return g_qwen21(p["prompt"], seed, prefix, w, h)
    if arm == "qwena":
        return g_qwena(p["prompt"], seed, prefix, w, h)
    if arm == "klein":
        return g_klein(p["prompt"], seed, prefix, w, h)
    raise SystemExit(f"arm {arm} is not part of the ComfyUI batteries (krea-dense, moss-prompt, qwen21, qwena, klein)")


# ------------------------------------------------------------------ ComfyUI client
def api(path, data=None, timeout=60):
    req = urllib.request.Request(COMFY + path, data=json.dumps(data).encode() if data is not None else None, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def upload(path, name):
    """multipart upload of an input image to ComfyUI (overwrite)."""
    b = uuid.uuid4().hex
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{name}\"\r\nContent-Type: image/png\r\n\r\n").encode() + Path(path).read_bytes() + \
           (f"\r\n--{b}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--{b}--\r\n").encode()
    req = urllib.request.Request(COMFY + "/upload/image", data=body, headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


class Vram:
    """whole-card used MiB, sampled every 0.5 s by one nvidia-smi process. It includes whatever else is resident on the card.
    Skipped (peak 0) when T004_VRAM=0 or nvidia-smi is missing."""
    def __init__(self):
        self.peak = 0
        self.p = None
        if os.environ.get("T004_VRAM", "1") == "0":
            return
        try:
            self.p = subprocess.Popen(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits", "-lms", "500"], stdout=subprocess.PIPE, text=True)
        except OSError:
            self.p = None
            return
        self.t = threading.Thread(target=self._read, daemon=True)
        self.t.start()

    def _read(self):
        for line in self.p.stdout:
            try:
                self.peak = max(self.peak, int(line.strip().splitlines()[0]))
            except ValueError:
                pass

    def stop(self):
        if self.p is None:
            return self.peak
        self.p.terminate()
        try:
            self.p.wait(5)
        except subprocess.TimeoutExpired:
            self.p.kill()
        return self.peak


def run_graph(graph, timeout=1500):
    v = Vram()
    t0 = time.time()
    try:
        pid = api("/prompt", {"prompt": graph, "client_id": uuid.uuid4().hex})["prompt_id"]
    except urllib.error.HTTPError as e:
        return dict(ok=False, error=e.read().decode()[:1500], peak_mib=v.stop(), wall=0, exec_s=None, images=[], prompt_id=None)
    while True:
        h = api(f"/history/{pid}")
        if pid in h:
            break
        if time.time() - t0 > timeout:
            return dict(ok=False, error="timeout", peak_mib=v.stop(), wall=round(time.time() - t0, 2), exec_s=None, images=[], prompt_id=pid)
        time.sleep(0.4)
    wall = round(time.time() - t0, 2)
    peak = v.stop()
    e = h[pid]
    msgs = {m[0]: m[1] for m in e["status"]["messages"]}
    ex = None
    if "execution_start" in msgs and "execution_success" in msgs:
        ex = round((msgs["execution_success"]["timestamp"] - msgs["execution_start"]["timestamp"]) / 1000, 2)
    ok = e["status"]["status_str"] == "success"
    imgs = [i for n in e["outputs"].values() for i in n.get("images", []) if i.get("type") == "output"]
    err = None if ok else json.dumps([m for m in e["status"]["messages"] if m[0] == "execution_error"])[:1500]
    return dict(ok=ok, error=err, peak_mib=peak, wall=wall, exec_s=ex, images=imgs, prompt_id=pid)


def fetch(img, dest):
    q = urllib.parse.urlencode({"filename": img["filename"], "subfolder": img["subfolder"], "type": img["type"]})
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(urllib.request.urlopen(COMFY + "/view?" + q, timeout=120).read())


def log(results, rec):
    results.parent.mkdir(parents=True, exist_ok=True)
    with open(results, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(json.dumps({k: rec[k] for k in ("arm", "brief", "seed", "ok", "exec_s", "wall", "peak_mib", "cold") if k in rec}), flush=True)


def done_set(results, phase):
    s = set()
    if results.exists():
        for line in results.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r.get("ok") and r.get("phase") == phase:
                s.add((r["arm"], r["brief"], r["seed"]))
    return s


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ------------------------------------------------------------------ jobs
def cmd_labels(arms, packs):
    spec = json.loads((PROMPTS / "briefs.json").read_text(encoding="utf-8"))
    assert spec["canvas"] == [W, H]
    for a in arms:
        if a not in ALL_ARMS:
            sys.exit(f"unknown arm {a}; arms: {', '.join(ALL_ARMS)} (FIBO runs through fibo_labels.py)")
    images = WORK / "images"
    images.mkdir(parents=True, exist_ok=True)
    if "krea-ie" in arms:
        for b in spec["briefs"]:
            if b["ie"]:
                ref = Path(packs) / b["ie"]["ref"]
                if not ref.exists():
                    sys.exit(f"krea-ie needs the reference image {ref} (not included in this repository)")
                upload(ref, pack_name(b))
    prev_arm = None
    for arm in arms:
        frozen = arm in FROZEN_ARMS
        results = WORK / ("results_gen.jsonl" if frozen else "results_extra.jsonl")
        done = done_set(results, "test")
        n, fails = 0, 0
        for b in spec["briefs"]:
            if arm == "krea-ie" and not b["ie"]:
                continue                       # no pack shot for this brief: arm not applicable
            for seed in spec["seeds"]:
                if (arm, b["id"], seed) in done:
                    continue
                dest = (images if frozen else images / arm) / f"{b['id']}_{arm}_{seed}.png"
                r = run_graph(build_label(arm, b, seed))
                rec = dict(phase="test", arm=arm, brief=b["id"], seed=seed, file=(dest.name if frozen else f"{arm}/{dest.name}"), ok=r["ok"], exec_s=r["exec_s"],
                           wall=r["wall"], peak_mib=r["peak_mib"], cold=(n == 0 and prev_arm != arm) if frozen else (n == 0), prompt_id=r["prompt_id"], error=r["error"], t_utc=now())
                if r["ok"]:
                    fetch(r["images"][0], dest)
                    fails = 0
                else:
                    fails += 1
                log(results, rec)
                n += 1
                if fails >= 2:
                    sys.exit(f"{arm}: two failures in a row, stopping (see {results})")
        prev_arm = arm


def cmd_battery(n, seeds, arms):
    """n = 2: prompts/battery2.json (or BATTERY_SPEC); n = 3: prompts/battery3.json. arm outer, seeds inner, so a model is loaded once."""
    if n == 2:
        spec_file = Path(os.environ.get("BATTERY_SPEC") or PROMPTS / "battery2.json")
        phase, prefix = "b2", "t004b2"
    else:
        spec_file = PROMPTS / "battery3.json"
        phase, prefix = "b3", "t004b3"
    spec = json.loads(spec_file.read_text(encoding="utf-8"))
    results = WORK / f"results_battery{n}.jsonl"
    d = done_set(results, phase)
    for arm in arms:
        n_done = 0
        out = WORK / "images" / f"battery{n}" / arm
        out.mkdir(parents=True, exist_ok=True)
        for seed, p in [(s, p) for s in seeds for p in spec["prompts"]]:
            if (arm, p["id"], seed) in d:
                continue
            dest = out / f"{p['id']}_{arm}_{seed}.png"
            r = run_graph(build_battery(arm, p, seed, f"{prefix}/{p['id']}_{arm}_{seed}"), timeout=1800)
            if r["ok"]:
                fetch(r["images"][0], dest)
            log(results, dict(phase=phase, arm=arm, brief=p["id"], seed=seed, canvas=p["canvas"], file=f"battery{n}/{arm}/{dest.name}", ok=r["ok"], exec_s=r["exec_s"], wall=r["wall"],
                              peak_mib=r["peak_mib"], cold=(n_done == 0), prompt_id=r["prompt_id"], error=r["error"], t_utc=now()))
            n_done += 1


def cmd_dump(out):
    """The graph of every arm for brief b03 (the lime can), seed 101: what workflows/comfyui/ holds."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    spec = json.loads((PROMPTS / "briefs.json").read_text(encoding="utf-8"))
    b = [x for x in spec["briefs"] if x["id"].startswith("b03")][0]
    for arm in ALL_ARMS:
        g = build_label(arm, b, 101)
        (out / f"workflow_{arm}_api.json").write_text(json.dumps(g, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("wrote", out)


def cmd_free():
    try:
        api("/free", {"unload_models": True, "free_memory": True}, timeout=20)
    except Exception as e:
        print("free failed", e)
    time.sleep(4)


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else ""
    args = sys.argv[2:]
    packs = WORK / "packs"
    if "--packs" in args:
        i = args.index("--packs")
        packs = Path(args[i + 1])
        args = args[:i] + args[i + 2:]
    if c == "labels" and args:
        cmd_labels(args, packs)
    elif c in ("battery2", "battery3") and len(args) > 1:
        cmd_battery(int(c[-1]), [int(x) for x in args[0].split(",")], args[1:])
    elif c == "dump" and len(args) == 1:
        cmd_dump(args[0])
    elif c == "free":
        cmd_free()
    else:
        sys.exit(__doc__)
