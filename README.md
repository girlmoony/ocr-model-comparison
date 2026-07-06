# OCR Model Comparison — DeepSeek-OCR-2 vs baidu/Unlimited-OCR

英単語帳（見開きのスマホ写真）を対象に、ローカルGPUで動くVLM系OCRモデル2種を検証・比較したリポジトリです。
従来のTesseractベースのOCRパイプラインで認識精度が不足していたため、その置き換え候補を評価しました。

- **[deepseek-ai/DeepSeek-OCR-2](https://huggingface.co/deepseek-ai/DeepSeek-OCR-2)** （約3.4B, BF16）
- **[baidu/Unlimited-OCR](https://huggingface.co/baidu/Unlimited-OCR)** （約3.3B, BF16）
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

| 指標 | Tesseract単独 | DeepSeek-OCR-2 | Unlimited-OCR |
|---|---|---|---|
| 見出し語 (word-recall) | 21/40 | **40/40** | 39/40 |
| 日本語の意味 | 0% | 28/40 | 27/40 |
| 英語例文 | 0% | **38/40** | 36/40 |
| 日本語訳 | 0% | 15/40 | **20/40** |
| 1枚あたり処理時間 | — | 31〜130秒 | **32〜52秒**（暴走時968秒） |
| ピークVRAM | — | 8.16 GB | 8.09 GB |

画像ごとの詳細は [docs/VLM_OCR_COMPARISON_JP.md](docs/VLM_OCR_COMPARISON_JP.md)、
Tesseractベースラインの評価は [docs/TESSERACT_BASELINE_JP.md](docs/TESSERACT_BASELINE_JP.md) を参照。

## 主な所見

1. **見出し語・英語例文は両モデルともほぼ完璧**。Tesseract（21/40）から劇的に改善し、辞書補正なしでも実用水準。
2. **両モデルとも5枚中1枚で繰り返しループが発生**（DeepSeek: IMG_4125 / Unlimited: IMG_4124）。crop無効・解像度1024pxへの設定変更リトライで復旧可能。実運用ではループ検知＋リトライ機構が必須。
3. **右端の細い日本語訳列は両者とも苦手**（欠落・類字誤認）。スマホ写真の画質限界であり、撮影品質の改善か辞書補正の併用が現実的。
4. 8GB VRAMではギリギリ動作（ピーク約8.1GB、一部共有メモリへ溢れるが完走）。

## 結論

総合精度はほぼ互角。**僅差で baidu/Unlimited-OCR を推奨**。

- 日本語訳列を拾う率が高く、正常時の処理時間が安定して短い
- ただし暴走時のダメージが大きいため `max_length=8192` に制限し、同一文字列の反復を検知したらbase設定（1024px・crop無効）でリトライするガードを入れること

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
│   ├── deepseek-ocr-2/            # DeepSeek-OCR-2 の生出力（result.mmd＋検出ボックス可視化）
│   │   ├── IMG_4125-freeocr/      # ループ時の再試行（Free OCRプロンプト）
│   │   └── IMG_4125-nocrop/       # ループ時の再試行（crop無効・1024px）→成功
│   └── unlimited-ocr/             # Unlimited-OCR の生出力（result.md＋検出ボックス可視化）
│       └── IMG_4124-base/         # ループ時の再試行（base設定）→成功
└── scripts/
    ├── run_ocr_bench.py           # 5枚一括推論（両モデル対応）
    ├── retry_one.py               # 1枚だけ設定を変えて再試行
    └── eval_ocr.py                # 期待JSONとの照合・採点
```

## 再現手順

### 1. 環境構築（venv×2、モデルごとにtransformersのバージョンが異なるため）

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
