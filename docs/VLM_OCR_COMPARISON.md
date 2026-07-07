# PaddleOCR vs DeepSeek-OCR (v1/Ollama) vs DeepSeek-OCR-2 vs baidu/Unlimited-OCR — Local GPU Benchmark Report

Conducted: 2026-07-06 to 07 / Environment: RTX 4060 Ti (8GB), Windows 11

The 5 images in `samples/ocr/` (two-page spreads of a vocabulary book photographed with a smartphone, 4032×3024) were OCR'd with all four systems and scored against `samples/ocr-expected/*.json`.

## Run Configuration

| | PaddleOCR | DeepSeek-OCR (v1) | DeepSeek-OCR-2 | baidu/Unlimited-OCR |
|---|---|---|---|---|
| Runtime | paddlepaddle-gpu 3.2.1 (cu126) | **Ollama 0.31.1** (`deepseek-ocr:latest`) | transformers (venv) | transformers (venv) |
| Model / precision | PP-OCRv6 medium det+rec, `lang=japan` | 3.3B / F16 | ~3.4B / BF16 | ~3.3B / BF16 |
| torch / transformers | — (Paddle runtime) | — (Ollama runtime) | 2.6.0+cu126 / 4.46.3 | 2.10.0+cu128 / 4.57.1 |
| Prompt | — (det+rec pipeline) | `Convert the document to markdown.` | `<image>\n<|grounding|>Convert the document to markdown. ` | `<image>document parsing.` |
| Resolution settings | default (max side 4000) | Ollama defaults (context 8192) | base_size=1024, image_size=768, crop_mode=True | base_size=1024, image_size=640, crop_mode=True |
| Peak VRAM | minimal | ~6.7GB (model size) | 8.16 GB | 8.09 GB |
| Time per page | **1.2–2.0 s** | 9–20 s | 31–130 s | 32–52 s (968 s when looping) |

## Accuracy (scored against expected JSON, fuzzy-match threshold 0.85)

8 entries per image × 5 images = 40 entries. Values in `()` are from a re-run with alternate settings after the model degenerated into a repetition loop.

### PaddleOCR (PP-OCRv6, lang=japan)

| sample | word-recall | meaning | exampleEn | exampleJa |
|---|---|---|---|---|
| IMG_4122 | 8/8 | 6/8 | 1/8 | 0/8 |
| IMG_4123 | 8/8 | 5/8 | 1/8 | 1/8 |
| IMG_4124 | 8/8 | 5/8 | 0/8 | 0/8 |
| IMG_4125 | 8/8 | 5/8 | 0/8 | 1/8 |
| section-11 | 8/8 | 7/8 | 0/8 | 0/8 |
| **Total** | **40/40** | **28/40** | **2/40** | **2/40** |

- By far the fastest (1.2–2.0 s per page after a 17 s pipeline load) with tiny models (~20 MB) and negligible VRAM. No loops, word order fully preserved.
- Character-level recognition is strong: headwords perfect, meanings tied with the best VLM (28/40).
- **The catastrophic example-sentence scores are a layout problem, not a recognition problem.** PaddleOCR emits raw text lines with no reading-order reconstruction, so sentences that wrap across lines in the multi-column spread come out as interleaved fragments (e.g. "The company" and "tried to suppress the" appear as separate, non-adjacent lines mixed with other columns' text). A post-processing step that sorts detection boxes into columns/rows would likely recover much of this — the box coordinates are available in the raw output.

### DeepSeek-OCR (v1) — Ollama

| sample | word-recall | meaning | exampleEn | exampleJa |
|---|---|---|---|---|
| IMG_4122 | 8/8 | 3/8 | 8/8 | 2/8 |
| IMG_4123 | 8/8 | 0/8 | 5/8 | 0/8 |
| IMG_4124 | 8/8 | 0/8 | 7/8 | 1/8 |
| IMG_4125 | 8/8 | 5/8 | 8/8 | 0/8 |
| section-11 | 8/8 | 0/8 | 8/8 | 0/8 |
| **Total** | **40/40** | **8/40** | **36/40** | **3/40** |

- No repetition loops on any of the 5 pages, and word order fully preserved (order 5/5). Output is clean per-word markdown.
- However, **the Japanese fields are frequently "reconstructed" rather than transcribed**: Chinese characters leak in (鎮圧→镇压, 飢餓→饥饿) and Japanese translations get rewritten (「彼は一番他人をだましそうにない人だ」→「彼は一番他人をだますし，そういった人に騙される」), which tanks the meaning/translation scores.
- Output volume is also small (735–1750 chars per page); details such as derived forms tend to be omitted.

### DeepSeek-OCR-2 — transformers

| sample | word-recall | meaning | exampleEn | exampleJa |
|---|---|---|---|---|
| IMG_4122 | 8/8 | 6/8 | 8/8 | 6/8 |
| IMG_4123 | 8/8 | 7/8 | 7/8 | 6/8 |
| IMG_4124 | 8/8 | 7/8 | 8/8 | 3/8 |
| IMG_4125 | 4/8 →(8/8) | 3/8 →(3/8) | 2/8 →(8/8) | 0/8 →(0/8) |
| section-11 | 8/8 | 5/8 | 7/8 | 0/8 |
| **Total (incl. retry)** | **40/40** | **28/40** | **38/40** | **15/40** |

- IMG_4125 collapsed into a repetition loop with the default settings. Recovered with `crop_mode=False, 1024px` (though the Japanese-translation column was still not captured).
- On section-11 the model mostly skipped the right-hand Japanese-translation column.

### baidu/Unlimited-OCR — transformers

| sample | word-recall | meaning | exampleEn | exampleJa |
|---|---|---|---|---|
| IMG_4122 | 8/8 | 6/8 | 8/8 | 5/8 |
| IMG_4123 | 7/8 | 3/8 | 5/8 | 6/8 |
| IMG_4124 | 1/8 →(8/8) | 0/8 →(6/8) | 1/8 →(7/8) | 0/8 →(1/8) |
| IMG_4125 | 8/8 | 5/8 | 8/8 | 6/8 |
| section-11 | 8/8 | 7/8 | 8/8 | 2/8 |
| **Total (incl. retry)** | **39/40** | **27/40** | **36/40** | **20/40** |

- IMG_4124 fell into an infinite repetition of "欢迎光临…" (968 s, 124KB) with the default settings (gundam: 640px+crop). Recovered with the base config (1024px, crop disabled, max_length=8192).

### Overall Comparison

| Metric | Tesseract only | PaddleOCR | DeepSeek-OCR (v1/Ollama) | DeepSeek-OCR-2 | Unlimited-OCR |
|---|---|---|---|---|---|
| Headwords (word-recall) | 21/40 | **40/40** | **40/40** | **40/40** | 39/40 |
| Japanese meanings | 0% | **28/40** | 8/40 | **28/40** | 27/40 |
| English examples | 0% | 2/40 | 36/40 | **38/40** | 36/40 |
| Japanese translations | 0% | 2/40 | 3/40 | 15/40 | **20/40** |
| Repetition loops | — | **0/5** | **0/5** | 1/5 | 1/5 |
| Time per page | — | **1.2–2.0 s** | 9–20 s | 31–130 s | 32–52 s |

## Observations

0. **PaddleOCR is in a different speed class** (1.2–2.0 s per page) with strong character recognition (headwords 40/40, meanings 28/40 — tied with the best VLM), but it has no layout understanding: multi-line sentences in the multi-column layout come out as interleaved fragments, so example-sentence fields are unusable without box-coordinate post-processing.
1. **Headwords and English examples are near-perfect for all three VLMs** — a dramatic improvement over Tesseract (21/40).
2. **For faithful transcription of Japanese, the two transformers models (v2 / Unlimited) are clearly superior.** v1/Ollama has a strong tendency to "read, summarize, and re-translate" the Japanese fields, with frequent Chinese contamination, making it unsuitable for verbatim extraction.
3. **v1/Ollama is exceptional in speed and stability** (9–20 s, zero loops, setup is just `ollama pull`). The images are most likely downscaled inside Ollama, and the resulting loss of fine Japanese glyphs appears to be one cause of its lower accuracy.
4. **v2 and Unlimited each hit a repetition loop on 1 of 5 images.** Recoverable by changing settings (disable crop / change resolution), but production use requires loop detection plus retry.
5. The narrow Japanese-translation column at the right edge is hard for every model. This is an image-quality limit of smartphone photos; improving capture quality or combining with dictionary correction is the realistic fix.

## Conclusions / Recommendations

- **If you need every field extracted verbatim (including Japanese meanings and translations)**: baidu/Unlimited-OCR or DeepSeek-OCR-2 (Unlimited recommended by a small margin — better capture rate on the Japanese-translation column and more consistent speed). Cap `max_length=8192` and add a repetition-detection retry guard.
- **If headwords + English examples are enough (Japanese filled in by dictionary correction)**: **DeepSeek-OCR (v1) + Ollama is the strongest option.** Word-recall 40/40, no loops, ~10 s per page, and setup is a single `ollama pull` — by far the lowest operational cost. Combined with the existing app's dictionary correction (`detectKnownPageCards`), it makes a practical pipeline.
- **If speed is paramount and headwords + meanings suffice (or you can invest in layout post-processing)**: **PaddleOCR** — 1–2 s per page out of the box; with column-aware sorting of its detection boxes, the example-sentence scores would likely improve substantially.
- If you truly need accurate extraction of the Japanese fields, the most effective step is improving capture quality (e.g., using a scanning app instead of plain photos).

## Artifacts

- `results/paddleocr/<name>/result.md` (PaddleOCR output, one text line per detection)
- `results/deepseek-ocr-v1-ollama/<name>/result.md` (Ollama output)
- `results/deepseek-ocr-2/<name>/result.mmd` (+ for the looped IMG_4125: `IMG_4125-freeocr/`, `IMG_4125-nocrop/`)
- `results/unlimited-ocr/<name>/result.md` (+ `IMG_4124-base/`)
- For the transformers models, `result_with_boxes.jpg` in each folder visualizes the detection boxes

## Reproduction

### PaddleOCR

```powershell
uv venv paddle-env --python 3.12
uv pip install --python paddle-env\Scripts\python.exe paddlepaddle-gpu==3.2.1 -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
uv pip install --python paddle-env\Scripts\python.exe paddleocr
paddle-env\Scripts\python.exe scripts\paddle_ocr.py samples\ocr results\paddleocr japan
```

### DeepSeek-OCR (v1) — Ollama

```powershell
ollama pull deepseek-ocr
python scripts\ollama_ocr.py samples\ocr results\deepseek-ocr-v1-ollama
```

### transformers models (two venvs — each model pins a different transformers version)

```powershell
# For DeepSeek-OCR-2
uv venv ds-env --python 3.12
uv pip install --python ds-env\Scripts\python.exe torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu126
uv pip install --python ds-env\Scripts\python.exe transformers==4.46.3 tokenizers==0.20.3 einops addict easydict pillow

# For Unlimited-OCR
uv venv baidu-env --python 3.12
uv pip install --python baidu-env\Scripts\python.exe torch==2.10.0 torchvision --index-url https://download.pytorch.org/whl/cu128
uv pip install --python baidu-env\Scripts\python.exe transformers==4.57.1 einops addict easydict pillow matplotlib

# Inference (first run downloads ~7GB per model)
ds-env\Scripts\python.exe scripts\run_ocr_bench.py --model deepseek --images samples\ocr --out results\deepseek-ocr-2
baidu-env\Scripts\python.exe scripts\run_ocr_bench.py --model baidu --images samples\ocr --out results\unlimited-ocr

# Scoring
ds-env\Scripts\python.exe scripts\eval_ocr.py samples\ocr-expected results\deepseek-ocr-2
```

Models are loaded with `AutoModel.from_pretrained(repo, trust_remote_code=True, torch_dtype=torch.bfloat16, _attn_implementation="eager")` and invoked via `model.infer(...)` (no flash-attn required).
