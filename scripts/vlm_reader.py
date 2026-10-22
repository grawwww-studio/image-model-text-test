#!/usr/bin/env python3
"""Optional second reader: a local vision-language model asked to transcribe the text in each image letter by letter (temperature 0, fixed seed,
thinking off). Talks to any OpenAI-compatible chat endpoint (we used a local llama.cpp server). Standard library only.
  VLM_URL=http://localhost:8080/v1/chat/completions VLM_MODEL=<name> vlm_reader.py OUT.json DIR [DIR ...]
Every *.png in the folders; resumable. In our run this reader failed the validity rule (specificity 0.77 on the controls: it corrects typos),
so it is a cross-check only. The model we used was a quantised 27B vision-language model; its exact name is not pinned here because the
reader did not matter for the verdict."""
import base64, glob, json, os, sys, time, urllib.request

URL = os.environ.get("VLM_URL", "http://localhost:8080/v1/chat/completions")
MODEL = os.environ.get("VLM_MODEL", "local-vision-model")
PROMPT = ("Transcribe every piece of text that is visible in this image, exactly as it is printed, letter by letter. Do not correct spelling, do not complete or "
          "guess words, and count repeated letters carefully (for example WWWW has four W). Write one line per line of text and nothing else. "
          "If a letter is cut off or unreadable, write it as it looks. If there is no text at all, write NONE.")


def ask(path):
    b = base64.b64encode(open(path, "rb").read()).decode()
    body = {"model": MODEL, "temperature": 0, "seed": 20261020, "max_tokens": 400, "cache_prompt": False,
            "chat_template_kwargs": {"enable_thinking": False},
            "messages": [{"role": "user", "content": [{"type": "text", "text": PROMPT}, {"type": "image_url", "image_url": {"url": "data:image/png;base64," + b}}]}]}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.load(r)["choices"][0]["message"]["content"].strip()


if len(sys.argv) < 3:
    sys.exit(__doc__)
out = sys.argv[1]
res = json.load(open(out)) if os.path.exists(out) else {"model": MODEL, "prompt": PROMPT, "items": {}}
for d in sys.argv[2:]:
    for f in sorted(glob.glob(os.path.join(d, "*.png"))):
        n = os.path.basename(f)
        if n in res["items"]:
            continue
        t = time.time()
        try:
            txt, err = ask(f), None
        except Exception as e:
            txt, err = "", f"{type(e).__name__}: {e}"[:300]
        res["items"][n] = {"text": txt, "seconds": round(time.time() - t, 2), "error": err}
        print(n, round(time.time() - t, 1), "s", repr(txt[:70]), err or "", flush=True)
        json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
