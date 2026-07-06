# -*- coding: utf-8 -*-
"""Compare VLM OCR outputs against samples/ocr-expected/*.json.

Metrics per image (8 vocab entries each):
  word-recall : headword appears in output (case-insensitive word boundary)
  word-order  : headwords appear in expected order
  meaning / exampleEn / exampleJa : fuzzy presence (similarity of best
    matching window >= 0.85 after normalization)
"""
import io
import json
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

EXPECTED_DIR = Path(sys.argv[1])
RESULTS_ROOT = Path(sys.argv[2])  # e.g. samples/ocr-results/deepseek-ocr-2


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"[\s　]+", "", s)
    s = re.sub(r"[、。,.;:；：・「」『』（）()\[\]<>|*_#~`'\"’‘“”!?！？…\-–—=/\\]", "", s)
    return s.lower()


def fuzzy_contains(haystack_norm: str, needle: str) -> float:
    n = normalize(needle)
    if not n:
        return 1.0
    if n in haystack_norm:
        return 1.0
    # sliding windows of needle length over haystack
    L = len(n)
    best = 0.0
    step = max(1, L // 4)
    for i in range(0, max(1, len(haystack_norm) - L // 2), step):
        win = haystack_norm[i : i + int(L * 1.3)]
        r = SequenceMatcher(None, n, win).ratio()
        if r > best:
            best = r
        if best > 0.98:
            break
    return best


def collect_output_text(d: Path) -> str:
    parts = []
    for p in sorted(d.rglob("*")):
        if p.suffix.lower() in (".md", ".mmd", ".txt", ".json") and p.is_file():
            try:
                parts.append(p.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                pass
    return "\n".join(parts)


TH = 0.85
total = {"word": [0, 0], "order": [0, 0], "meaning": [0, 0], "en": [0, 0], "ja": [0, 0]}
print(f"{'sample':<12} word-recall  word-order  meaning  exampleEn  exampleJa")
for exp_file in sorted(EXPECTED_DIR.glob("*.json")):
    stem = exp_file.stem
    out_dir = RESULTS_ROOT / stem
    if not out_dir.exists():
        print(f"{stem:<12} (no output)")
        continue
    entries = json.loads(exp_file.read_text(encoding="utf-8"))
    raw = collect_output_text(out_dir)
    raw_norm = normalize(raw)
    raw_lower = raw.lower()

    n = len(entries)
    wr = sum(1 for e in entries if re.search(rf"\b{re.escape(e['word'].lower())}\b", raw_lower))
    pos = [raw_lower.find(e["word"].lower()) for e in entries]
    found_pos = [p for p in pos if p >= 0]
    order_ok = 1 if (len(found_pos) == n and found_pos == sorted(found_pos)) else 0
    mg = sum(1 for e in entries if fuzzy_contains(raw_norm, e["meaning"]) >= TH)
    en = sum(1 for e in entries if fuzzy_contains(raw_norm, e["exampleEn"]) >= TH)
    ja = sum(1 for e in entries if fuzzy_contains(raw_norm, e["exampleJa"]) >= TH)

    total["word"][0] += wr; total["word"][1] += n
    total["order"][0] += order_ok; total["order"][1] += 1
    total["meaning"][0] += mg; total["meaning"][1] += n
    total["en"][0] += en; total["en"][1] += n
    total["ja"][0] += ja; total["ja"][1] += n
    print(f"{stem:<12} {wr}/{n:<10} {order_ok:<11} {mg}/{n:<6} {en}/{n:<8} {ja}/{n}")

t = total
print(f"\nTOTAL word-recall={t['word'][0]}/{t['word'][1]} "
      f"order={t['order'][0]}/{t['order'][1]} meaning={t['meaning'][0]}/{t['meaning'][1]} "
      f"exampleEn={t['en'][0]}/{t['en'][1]} exampleJa={t['ja'][0]}/{t['ja'][1]}")
