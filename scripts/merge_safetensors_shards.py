#!/usr/bin/env python3
"""Stream-merge safetensors shards into one file without loading tensors into RAM (the HF Qwen3-VL-4B text encoder ships as 2 shards; ComfyUI's CLIPLoader wants one file).
Tensor names, dtypes and bytes are copied unchanged. Usage: merge_safetensors_shards.py OUT SHARD1 SHARD2 ...   (prints sha256 of the output)"""
import hashlib
import json
import struct
import sys


def read_header(path):
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        return json.loads(f.read(n)), 8 + n


def main(out, shards):
    items = []   # (name, meta, shard, abs_start)
    for s in shards:
        h, base = read_header(s)
        for k, v in h.items():
            if k == "__metadata__":
                continue
            items.append((k, v, s, base + v["data_offsets"][0]))
    new, pos = {"__metadata__": {"format": "pt"}}, 0
    for k, v, _, _ in items:
        size = v["data_offsets"][1] - v["data_offsets"][0]
        new[k] = {"dtype": v["dtype"], "shape": v["shape"], "data_offsets": [pos, pos + size]}
        pos += size
    hb = json.dumps(new, separators=(",", ":")).encode()
    hb += b" " * ((8 - len(hb) % 8) % 8)
    hsh = hashlib.sha256()
    handles = {s: open(s, "rb") for s in shards}
    with open(out, "wb") as o:
        for chunk in (struct.pack("<Q", len(hb)), hb):
            o.write(chunk)
            hsh.update(chunk)
        for k, v, s, start in items:
            size = v["data_offsets"][1] - v["data_offsets"][0]
            f = handles[s]
            f.seek(start)
            left = size
            while left:
                b = f.read(min(left, 1 << 24))
                if not b:
                    raise SystemExit("short read " + k)
                o.write(b)
                hsh.update(b)
                left -= len(b)
    print("wrote", out, "tensors", len(items), "bytes", 8 + len(hb) + pos, "sha256", hsh.hexdigest())


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
