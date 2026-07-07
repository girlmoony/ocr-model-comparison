# -*- coding: utf-8 -*-
"""Run PaddleOCR-VL document parsing on images.

Usage: python paddle_vl_ocr.py <images_dir> <out_root> [pipeline_version]
"""
import io
import json
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from paddleocr import PaddleOCRVL

images_dir = Path(sys.argv[1])
out_root = Path(sys.argv[2])
version = sys.argv[3] if len(sys.argv) > 3 else "v1.6"

t0 = time.time()
pipeline = PaddleOCRVL(pipeline_version=version)
print(f"[load] PaddleOCRVL {version} in {time.time() - t0:.1f}s", flush=True)

images = sorted(p for p in images_dir.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg"))
out_root.mkdir(parents=True, exist_ok=True)
timings = {}

for img in images:
    print(f"===== {img.name} =====", flush=True)
    t0 = time.time()
    try:
        output = pipeline.predict(str(img))
        out_dir = out_root / img.stem
        out_dir.mkdir(parents=True, exist_ok=True)
        for res in output:
            res.save_to_markdown(save_path=str(out_dir))
            res.save_to_json(save_path=str(out_dir))
        dt = time.time() - t0
        timings[img.name] = round(dt, 1)
        print(f"[time] {dt:.1f}s", flush=True)
    except Exception:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        timings[img.name] = -1

(out_root / "timings.json").write_text(json.dumps(timings, indent=2), encoding="utf-8")
print("[done]", json.dumps(timings))
