# -*- coding: utf-8 -*-
"""OCR benchmark runner for DeepSeek-OCR-2 / baidu Unlimited-OCR.

Usage:
  python run_ocr_bench.py --model deepseek --images <dir> --out <dir>
  python run_ocr_bench.py --model baidu    --images <dir> --out <dir>
"""
import argparse
import io
import json
import sys
import time
import traceback
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import torch
from transformers import AutoModel, AutoTokenizer

CONFIGS = {
    "deepseek": {
        "repo": "deepseek-ai/DeepSeek-OCR-2",
        "prompt": "<image>\n<|grounding|>Convert the document to markdown. ",
        "infer_kwargs": dict(base_size=1024, image_size=768, crop_mode=True),
    },
    "baidu": {
        "repo": "baidu/Unlimited-OCR",
        "prompt": "<image>document parsing.",
        "infer_kwargs": dict(base_size=1024, image_size=640, crop_mode=True, max_length=32768),
    },
}


def load_model(repo):
    tokenizer = AutoTokenizer.from_pretrained(repo, trust_remote_code=True)
    last_err = None
    for attn in ("flash_attention_2", "sdpa", "eager"):
        try:
            model = AutoModel.from_pretrained(
                repo,
                _attn_implementation=attn,
                trust_remote_code=True,
                use_safetensors=True,
                torch_dtype=torch.bfloat16,
            )
            print(f"[load] attn_implementation={attn}")
            return tokenizer, model.eval().cuda()
        except Exception as e:  # noqa: BLE001
            last_err = e
            print(f"[load] {attn} failed: {type(e).__name__}: {e}")
    raise last_err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=list(CONFIGS), required=True)
    ap.add_argument("--images", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    cfg = CONFIGS[args.model]
    images = sorted(
        p for p in Path(args.images).iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg")
    )
    if not images:
        print("no images found", file=sys.stderr)
        sys.exit(1)
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    print(f"[load] {cfg['repo']} ...")
    t0 = time.time()
    tokenizer, model = load_model(cfg["repo"])
    print(f"[load] done in {time.time() - t0:.1f}s, "
          f"vram={torch.cuda.memory_allocated() / 1e9:.2f}GB")

    timings = {}
    for img in images:
        out_dir = out_root / img.stem
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n===== {img.name} =====")
        t0 = time.time()
        attempts = [cfg["infer_kwargs"], dict(cfg["infer_kwargs"], crop_mode=False)]
        res, err = None, None
        for i, kw in enumerate(attempts):
            try:
                torch.cuda.empty_cache()
                res = model.infer(
                    tokenizer,
                    prompt=cfg["prompt"],
                    image_file=str(img),
                    output_path=str(out_dir),
                    save_results=True,
                    **kw,
                )
                err = None
                break
            except torch.cuda.OutOfMemoryError as e:
                err = e
                print(f"[oom] attempt {i} kwargs={kw} -> retrying smaller")
            except Exception as e:  # noqa: BLE001
                err = e
                traceback.print_exc()
                break
        dt = time.time() - t0
        timings[img.name] = round(dt, 1)
        print(f"[time] {img.name}: {dt:.1f}s  "
              f"peak_vram={torch.cuda.max_memory_allocated() / 1e9:.2f}GB")
        torch.cuda.reset_peak_memory_stats()
        if isinstance(res, str) and res.strip():
            (out_dir / "result_text.md").write_text(res, encoding="utf-8")
        if err is not None:
            (out_dir / "error.txt").write_text(repr(err), encoding="utf-8")

    (out_root / "timings.json").write_text(json.dumps(timings, indent=2), encoding="utf-8")
    print("\n[done]", json.dumps(timings))


if __name__ == "__main__":
    main()
