# -*- coding: utf-8 -*-
"""Retry a single image with alternate settings.
Usage: python retry_one.py <repo> <image> <out_dir> <prompt> <base_size> <image_size> <crop:0|1> [max_length]
"""
import io
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import torch
from transformers import AutoModel, AutoTokenizer

repo, image, out_dir, prompt = sys.argv[1:5]
base_size, image_size, crop = int(sys.argv[5]), int(sys.argv[6]), bool(int(sys.argv[7]))
kw = {}
if len(sys.argv) > 8:
    kw["max_length"] = int(sys.argv[8])

tokenizer = AutoTokenizer.from_pretrained(repo, trust_remote_code=True)
model = None
for attn in ("sdpa", "eager"):
    try:
        model = AutoModel.from_pretrained(
            repo, _attn_implementation=attn, trust_remote_code=True,
            use_safetensors=True, torch_dtype=torch.bfloat16,
        ).eval().cuda()
        print(f"[load] attn={attn}")
        break
    except Exception as e:  # noqa: BLE001
        print(f"[load] {attn} failed: {e}")
assert model is not None

import pathlib
pathlib.Path(out_dir).mkdir(parents=True, exist_ok=True)
t0 = time.time()
res = model.infer(tokenizer, prompt=prompt, image_file=image, output_path=out_dir,
                  base_size=base_size, image_size=image_size, crop_mode=crop,
                  save_results=True, **kw)
print(f"[time] {time.time() - t0:.1f}s peak_vram={torch.cuda.max_memory_allocated()/1e9:.2f}GB")
if isinstance(res, str) and res.strip():
    (pathlib.Path(out_dir) / "result_text.md").write_text(res, encoding="utf-8")
