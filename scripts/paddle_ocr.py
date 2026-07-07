# -*- coding: utf-8 -*-
"""Run PaddleOCR on images.

Usage: python paddle_ocr.py <images_dir> <out_root> [lang]
"""
import io
import json
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from paddleocr import PaddleOCR

images_dir = Path(sys.argv[1])
out_root = Path(sys.argv[2])
lang = sys.argv[3] if len(sys.argv) > 3 else "japan"

t0 = time.time()
ocr = PaddleOCR(
    lang=lang,
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=True,
)
print(f"[load] PaddleOCR lang={lang} in {time.time() - t0:.1f}s", flush=True)

images = sorted(p for p in images_dir.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg"))
out_root.mkdir(parents=True, exist_ok=True)
timings = {}

for img in images:
    print(f"===== {img.name} =====", flush=True)
    t0 = time.time()
    try:
        result = ocr.predict(str(img))
        lines = []
        for res in result:
            d = res if isinstance(res, dict) else getattr(res, "json", {}).get("res", {})
            texts = d.get("rec_texts") or []
            lines.extend(texts)
        dt = time.time() - t0
        timings[img.name] = round(dt, 1)
        out_dir = out_root / img.stem
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "result.md").write_text("\n".join(lines), encoding="utf-8")
        print(f"[time] {dt:.1f}s  lines={len(lines)}", flush=True)
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        timings[img.name] = -1

(out_root / "timings.json").write_text(json.dumps(timings, indent=2), encoding="utf-8")
print("[done]", json.dumps(timings))
