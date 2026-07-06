# OCR Model Comparison — DeepSeek-OCR (v1/Ollama) vs DeepSeek-OCR-2 vs baidu/Unlimited-OCR

英単語帳（見開きのスマホ写真）を対象に、ローカルGPUで動くVLM系OCRモデル3種を検証・比較したリポジトリです。
従来のTesseractベースのOCRパイプラインで認識精度が不足していたため、その置き換え候補を評価しました。

- **[deepseek-ai/DeepSeek-OCR](https://huggingface.co/deepseek-ai/DeepSeek-OCR)** （3.3B, F16）— **Ollama** (`deepseek-ocr:latest`) で実行
- **[deepseek-ai/DeepSeek-OCR-2](https://huggingface.co/deepseek-ai/DeepSeek-OCR-2)** （約3.4B, BF16）— transformers で実行
- **[baidu/Unlimited-OCR](https://huggingface.co/baidu/Unlimited-OCR)** （約3.3B, BF16）— transformers で実行
- 参考ベースライン: Tesseract（既存パイプライン）

## 検証環境

| 項目 | 内容 |
|---|---|
| GPU | NVIDIA GeForce RTX 4060 Ti (8GB VRAM) |
| OS | Windows 11 |
| Python | 3.12 (uv venv) |
| attention | eager（flash-attnはWindows未対応のため不使用） |
| 入力 | `samples/ocr/` の5枚（4032×3024のスマホ写真、各8単語エントリ） |
| 正解データ | `samples/ocr-expected/*.json`（単語・発音・意味・英例文・日本語訳） |

## 結果サマリ（5枚 × 8エントリ = 40エントリ）

fuzzy一致しきい値0.85で採点。暴走（繰り返しループ）した画像は代替設定での再実行値を採用。

| 指標 | Tesseract単独 | DeepSeek-OCR (v1/Ollama) | DeepSeek-OCR-2 | Unlimited-OCR |
|---|---|---|---|---|
| 見出し語 (word-recall) | 21/40 | **40/40** | **40/40** | 39/40 |
| 日本語の意味 | 0% | 8/40 | **28/40** | 27/40 |
| 英語例文 | 0% | 36/40 | **38/40** | 36/40 |
| 日本語訳 | 0% | 3/40 | 15/40 | **20/40** |
| 繰り返しループ | — | **0/5** | 1/5 | 1/5 |
| 1枚あたり処理時間 | — | **9〜20秒** | 31〜130秒 | 32〜52秒（暴走時968秒） |
| ピークVRAM | — | 約6.7GB | 8.16 GB | 8.09 GB |

画像ごとの詳細は [docs/VLM_OCR_COMPARISON_JP.md](docs/VLM_OCR_COMPARISON_JP.md)、
Tesseractベースラインの評価は [docs/TESSERACT_BASELINE_JP.md](docs/TESSERACT_BASELINE_JP.md) を参照。

## 主な所見

1. **見出し語・英語例文は3モデルともほぼ完璧**。Tesseract（21/40）から劇的に改善し、辞書補正なしでも実用水準。
2. **日本語の忠実な転写は transformers 系2モデル（v2 / Unlimited）が明確に優位**。v1/Ollamaは日本語欄を要約・翻訳し直す挙動が強く中国語も混入するため、原文どおりの抽出には不向き（meaning 8/40, exampleJa 3/40）。
3. **v1/Ollamaは速度と安定性が突出**（9〜20秒/枚、ループゼロ、導入は`ollama pull`のみ）。
4. **v2とUnlimitedは5枚中1枚で繰り返しループが発生**（DeepSeek-2: IMG_4125 / Unlimited: IMG_4124）。crop無効・解像度1024pxへの設定変更リトライで復旧可能。実運用ではループ検知＋リトライ機構が必須。
5. **右端の細い日本語訳列は全モデル苦手**（欠落・類字誤認）。スマホ写真の画質限界であり、撮影品質の改善か辞書補正の併用が現実的。
6. transformers系は8GB VRAMでギリギリ動作（ピーク約8.1GB、一部共有メモリへ溢れるが完走）。

## 結論

用途で選ぶのが正解。

- **全フィールド（日本語の意味・訳も原文どおり）欲しい場合**: **baidu/Unlimited-OCR**（僅差でDeepSeek-OCR-2より推奨）。`max_length=8192` 制限＋反復検知時にbase設定（1024px・crop無効）でリトライするガードを入れること。
- **見出し語＋英語例文が取れれば良い場合（日本語は辞書補正で補完）**: **DeepSeek-OCR (v1) + Ollama が最有力**。word-recall 40/40・ループなし・1枚10秒前後で運用コストが圧倒的に低い。

## リポジトリ構成

```
├── README.md
├── docs/
│   ├── VLM_OCR_COMPARISON_JP.md   # 詳細比較レポート
│   └── TESSERACT_BASELINE_JP.md   # Tesseractベースライン評価
├── samples/
│   ├── ocr/                       # 入力画像5枚（単語帳の見開き写真）
│   └── ocr-expected/              # 正解JSON（8エントリ×5枚）
├── results/
│   ├── deepseek-ocr-v1-ollama/    # DeepSeek-OCR (v1) の生出力（Ollama経由、result.md）
│   ├── deepseek-ocr-2/            # DeepSeek-OCR-2 の生出力（result.mmd＋検出ボックス可視化）
│   │   ├── IMG_4125-freeocr/      # ループ時の再試行（Free OCRプロンプト）
│   │   └── IMG_4125-nocrop/       # ループ時の再試行（crop無効・1024px）→成功
│   └── unlimited-ocr/             # Unlimited-OCR の生出力（result.md＋検出ボックス可視化）
│       └── IMG_4124-base/         # ループ時の再試行（base設定）→成功
└── scripts/
    ├── run_ocr_bench.py           # 5枚一括推論（transformers系2モデル対応）
    ├── ollama_ocr.py              # Ollama経由の一括推論（deepseek-ocr）
    ├── retry_one.py               # 1枚だけ設定を変えて再試行
    └── eval_ocr.py                # 期待JSONとの照合・採点
```

## 再現手順

### 0. DeepSeek-OCR (v1) — Ollama（最も簡単）

```powershell
ollama pull deepseek-ocr
python scripts\ollama_ocr.py samples\ocr results\deepseek-ocr-v1-ollama
python scripts\eval_ocr.py samples\ocr-expected results\deepseek-ocr-v1-ollama
```

### 1. transformers系の環境構築（venv×2、モデルごとにtransformersのバージョンが異なるため）

```powershell
# DeepSeek-OCR-2 用
uv venv ds-env --python 3.12
uv pip install --python ds-env\Scripts\python.exe torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu126
uv pip install --python ds-env\Scripts\python.exe transformers==4.46.3 tokenizers==0.20.3 einops addict easydict pillow

# Unlimited-OCR 用
uv venv baidu-env --python 3.12
uv pip install --python baidu-env\Scripts\python.exe torch==2.10.0 torchvision --index-url https://download.pytorch.org/whl/cu128
uv pip install --python baidu-env\Scripts\python.exe transformers==4.57.1 einops addict easydict pillow matplotlib
```

### 2. 推論（初回はモデル約7GBを自動ダウンロード）

```powershell
ds-env\Scripts\python.exe scripts\run_ocr_bench.py --model deepseek --images samples\ocr --out results\deepseek-ocr-2
baidu-env\Scripts\python.exe scripts\run_ocr_bench.py --model baidu --images samples\ocr --out results\unlimited-ocr
```

### 3. 採点

```powershell
ds-env\Scripts\python.exe scripts\eval_ocr.py samples\ocr-expected results\deepseek-ocr-2
ds-env\Scripts\python.exe scripts\eval_ocr.py samples\ocr-expected results\unlimited-ocr
```

## 注意

`samples/ocr/` の画像は市販の英単語帳を撮影したものです。著作権保護のため、このリポジトリは**プライベート**での運用を前提としています。
