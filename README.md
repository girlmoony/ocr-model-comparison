# OCR Model Comparison — DeepSeek-OCR (v1/Ollama) vs DeepSeek-OCR-2 vs baidu/Unlimited-OCR

A benchmark of three local-GPU VLM OCR models on smartphone photos of an English vocabulary book (two-page spreads).
The existing Tesseract-based OCR pipeline did not deliver sufficient accuracy, so these models were evaluated as replacement candidates.

- **[deepseek-ai/DeepSeek-OCR](https://huggingface.co/deepseek-ai/DeepSeek-OCR)** (3.3B, F16) — run via **Ollama** (`deepseek-ocr:latest`)
- **[deepseek-ai/DeepSeek-OCR-2](https://huggingface.co/deepseek-ai/DeepSeek-OCR-2)** (~3.4B, BF16) — run via transformers
- **[baidu/Unlimited-OCR](https://huggingface.co/baidu/Unlimited-OCR)** (~3.3B, BF16) — run via transformers
- Reference baseline: Tesseract (existing pipeline)

## Test Environment

| Item | Details |
|---|---|
| GPU | NVIDIA GeForce RTX 4060 Ti (8GB VRAM) |
| OS | Windows 11 |
| Python | 3.12 (uv venv) |
| Attention | eager (flash-attn is not available on Windows) |
| Input | 5 images in `samples/ocr/` (4032×3024 smartphone photos, 8 vocabulary entries each) |
| Ground truth | `samples/ocr-expected/*.json` (word, pronunciation, meaning, English example, Japanese translation) |

## Results Summary (5 images × 8 entries = 40 entries)

Scored with a fuzzy-match threshold of 0.85. For images where a model degenerated into a repetition loop, the score from a re-run with alternate settings is used.

| Metric | Tesseract only | DeepSeek-OCR (v1/Ollama) | DeepSeek-OCR-2 | Unlimited-OCR |
|---|---|---|---|---|
| Headwords (word-recall) | 21/40 | **40/40** | **40/40** | 39/40 |
| Japanese meanings | 0% | 8/40 | **28/40** | 27/40 |
| English examples | 0% | 36/40 | **38/40** | 36/40 |
| Japanese translations | 0% | 3/40 | 15/40 | **20/40** |
| Repetition loops | — | **0/5** | 1/5 | 1/5 |
| Time per page | — | **9–20 s** | 31–130 s | 32–52 s (968 s when looping) |
| Peak VRAM | — | ~6.7 GB | 8.16 GB | 8.09 GB |

Per-image details: [docs/VLM_OCR_COMPARISON.md](docs/VLM_OCR_COMPARISON.md).
Tesseract baseline evaluation: [docs/TESSERACT_BASELINE.md](docs/TESSERACT_BASELINE.md).

## Key Findings

1. **Headwords and English examples are near-perfect across all three models** — a dramatic improvement over Tesseract (21/40), practical even without dictionary correction.
2. **For faithful transcription of Japanese text, the two transformers models (v2 / Unlimited) are clearly superior.** v1/Ollama tends to paraphrase and re-translate the Japanese fields, and frequently mixes in Chinese characters, making it unsuitable for verbatim extraction (meaning 8/40, exampleJa 3/40).
3. **v1/Ollama stands out for speed and stability** (9–20 s per page, zero loops, setup is just `ollama pull`).
4. **v2 and Unlimited each hit a repetition loop on 1 of 5 images** (DeepSeek-2: IMG_4125 / Unlimited: IMG_4124). Recoverable by retrying with crop disabled at 1024 px; production use requires loop detection plus retry.
5. **The narrow Japanese-translation column on the right edge is hard for every model** (dropped or misread characters). This is an image-quality limit of smartphone photos; better capture quality or dictionary-based correction is the realistic fix.
6. The transformers models barely fit in 8GB VRAM (peak ~8.1 GB, partially spilling into shared memory but completing).

## Conclusion

Choose by use case.

- **If you need every field (Japanese meanings and translations, verbatim)**: **baidu/Unlimited-OCR** (recommended over DeepSeek-OCR-2 by a small margin). Cap `max_length=8192` and add a guard that retries with the base config (1024 px, crop disabled) when repetition is detected.
- **If headwords + English examples are enough (Japanese filled in by dictionary correction)**: **DeepSeek-OCR (v1) + Ollama is the strongest option** — word-recall 40/40, no loops, ~10 s per page, and by far the lowest operational cost.

## Repository Layout

```
├── README.md
├── docs/
│   ├── VLM_OCR_COMPARISON.md      # Detailed comparison report
│   └── TESSERACT_BASELINE.md      # Tesseract baseline evaluation
├── samples/
│   ├── ocr/                       # 5 input images (vocabulary book spreads)
│   └── ocr-expected/              # Ground-truth JSON (8 entries × 5 images)
├── results/
│   ├── deepseek-ocr-v1-ollama/    # DeepSeek-OCR (v1) raw output via Ollama (result.md)
│   ├── deepseek-ocr-2/            # DeepSeek-OCR-2 raw output (result.mmd + detection-box overlay)
│   │   ├── IMG_4125-freeocr/      # Loop retry (Free OCR prompt)
│   │   └── IMG_4125-nocrop/       # Loop retry (crop disabled, 1024 px) → success
│   └── unlimited-ocr/             # Unlimited-OCR raw output (result.md + detection-box overlay)
│       └── IMG_4124-base/         # Loop retry (base config) → success
└── scripts/
    ├── run_ocr_bench.py           # Batch inference for the two transformers models
    ├── ollama_ocr.py              # Batch inference via Ollama (deepseek-ocr)
    ├── retry_one.py               # Re-run a single image with alternate settings
    └── eval_ocr.py                # Scoring against the ground-truth JSON
```

## Reproduction

### 0. DeepSeek-OCR (v1) — Ollama (easiest)

```powershell
ollama pull deepseek-ocr
python scripts\ollama_ocr.py samples\ocr results\deepseek-ocr-v1-ollama
python scripts\eval_ocr.py samples\ocr-expected results\deepseek-ocr-v1-ollama
```

### 1. Environment setup for the transformers models (two venvs — each model pins a different transformers version)

```powershell
# For DeepSeek-OCR-2
uv venv ds-env --python 3.12
uv pip install --python ds-env\Scripts\python.exe torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu126
uv pip install --python ds-env\Scripts\python.exe transformers==4.46.3 tokenizers==0.20.3 einops addict easydict pillow

# For Unlimited-OCR
uv venv baidu-env --python 3.12
uv pip install --python baidu-env\Scripts\python.exe torch==2.10.0 torchvision --index-url https://download.pytorch.org/whl/cu128
uv pip install --python baidu-env\Scripts\python.exe transformers==4.57.1 einops addict easydict pillow matplotlib
```

### 2. Inference (first run downloads ~7GB per model)

```powershell
ds-env\Scripts\python.exe scripts\run_ocr_bench.py --model deepseek --images samples\ocr --out results\deepseek-ocr-2
baidu-env\Scripts\python.exe scripts\run_ocr_bench.py --model baidu --images samples\ocr --out results\unlimited-ocr
```

### 3. Scoring

```powershell
ds-env\Scripts\python.exe scripts\eval_ocr.py samples\ocr-expected results\deepseek-ocr-2
ds-env\Scripts\python.exe scripts\eval_ocr.py samples\ocr-expected results\unlimited-ocr
```
