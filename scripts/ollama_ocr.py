# -*- coding: utf-8 -*-
"""Run OCR on images via local Ollama (deepseek-ocr).

Usage: python ollama_ocr.py <images_dir> <out_root> [model] [prompt]
"""
import base64
import io
import json
import sys
import time
import urllib.request
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

images_dir = Path(sys.argv[1])
out_root = Path(sys.argv[2])
model = sys.argv[3] if len(sys.argv) > 3 else "deepseek-ocr:latest"
prompt = sys.argv[4] if len(sys.argv) > 4 else "Convert the document to markdown."

images = sorted(p for p in images_dir.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg"))
out_root.mkdir(parents=True, exist_ok=True)
timings = {}

for img in images:
    b64 = base64.b64encode(img.read_bytes()).decode()
    payload = {
        "model": model,
        "prompt": prompt,
        "images": [b64],
        "stream": False,
        "options": {"temperature": 0, "num_predict": 8192},
        "keep_alive": "10m",
    }
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    print(f"===== {img.name} =====", flush=True)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=1800) as r:
            body = json.loads(r.read().decode("utf-8"))
        text = body.get("response", "")
        dt = time.time() - t0
        timings[img.name] = round(dt, 1)
        out_dir = out_root / img.stem
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "result.md").write_text(text, encoding="utf-8")
        print(f"[time] {dt:.1f}s  chars={len(text)}  "
              f"eval_count={body.get('eval_count')}  done_reason={body.get('done_reason')}",
              flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"[error] {img.name}: {e}", flush=True)
        timings[img.name] = -1

(out_root / "timings.json").write_text(json.dumps(timings, indent=2), encoding="utf-8")
print("[done]", json.dumps(timings))
