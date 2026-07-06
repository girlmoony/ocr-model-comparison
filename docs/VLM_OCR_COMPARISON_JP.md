# DeepSeek-OCR (v1/Ollama) vs DeepSeek-OCR-2 vs baidu/Unlimited-OCR ローカルGPU検証レポート

実施日: 2026-07-06〜07 / 環境: RTX 4060 Ti (8GB), Windows 11

`samples/ocr/` の5枚（単語帳の見開き写真、4032×3024）を3モデルでOCRし、`samples/ocr-expected/*.json` と照合した。

## 実行構成

| | DeepSeek-OCR (v1) | DeepSeek-OCR-2 | baidu/Unlimited-OCR |
|---|---|---|---|
| 実行方法 | **Ollama 0.31.1** (`deepseek-ocr:latest`) | transformers (venv) | transformers (venv) |
| パラメータ数 / 精度 | 3.3B / F16 | 約3.4B / BF16 | 約3.3B / BF16 |
| torch / transformers | —（Ollamaランタイム） | 2.6.0+cu126 / 4.46.3 | 2.10.0+cu128 / 4.57.1 |
| プロンプト | `Convert the document to markdown.` | `<image>\n<|grounding|>Convert the document to markdown. ` | `<image>document parsing.` |
| 解像度設定 | Ollama既定（context 8192） | base_size=1024, image_size=768, crop_mode=True | base_size=1024, image_size=640, crop_mode=True |
| ピークVRAM | 約6.7GB（モデルサイズ） | 8.16 GB | 8.09 GB |
| 1枚あたり時間 | **9〜20秒** | 31〜130秒 | 32〜52秒（暴走時968秒） |

## 精度（期待JSONとの照合、fuzzy一致しきい値0.85）

各画像8エントリ × 5枚 = 40エントリ。`()` は暴走した画像を代替設定で再実行した値。

### DeepSeek-OCR (v1) — Ollama

| sample | word-recall | meaning | exampleEn | exampleJa |
|---|---|---|---|---|
| IMG_4122 | 8/8 | 3/8 | 8/8 | 2/8 |
| IMG_4123 | 8/8 | 0/8 | 5/8 | 0/8 |
| IMG_4124 | 8/8 | 0/8 | 7/8 | 1/8 |
| IMG_4125 | 8/8 | 5/8 | 8/8 | 0/8 |
| section-11 | 8/8 | 0/8 | 8/8 | 0/8 |
| **合計** | **40/40** | **8/40** | **36/40** | **3/40** |

- 5枚とも繰り返しループなし・語順も完全（order 5/5）。出力は単語ごとに整った markdown。
- ただし**日本語欄は「転写」ではなく「再構成」が多い**。中国語の混入（鎮圧→镇压、飢餓→饥饿）や、日本語訳の書き換え（「彼は一番他人をだましそうにない人だ」→「彼は一番他人をだますし，そういった人に騙される」）が頻発し、意味・日本語訳のスコアが大きく落ちる。
- 出力量も少なめ（735〜1750文字/枚）で、派生語などの細部は省略されがち。

### DeepSeek-OCR-2 — transformers

| sample | word-recall | meaning | exampleEn | exampleJa |
|---|---|---|---|---|
| IMG_4122 | 8/8 | 6/8 | 8/8 | 6/8 |
| IMG_4123 | 8/8 | 7/8 | 7/8 | 6/8 |
| IMG_4124 | 8/8 | 7/8 | 8/8 | 3/8 |
| IMG_4125 | 4/8 →(8/8) | 3/8 →(3/8) | 2/8 →(8/8) | 0/8 →(0/8) |
| section-11 | 8/8 | 5/8 | 7/8 | 0/8 |
| **合計(再試行込)** | **40/40** | **28/40** | **38/40** | **15/40** |

- IMG_4125 は既定設定で繰り返しループに陥り出力崩壊。`crop_mode=False, 1024px` で復旧（ただし日本語訳列は取得できず）。
- section-11 では右列の日本語訳をほぼ読み飛ばす傾向。

### baidu/Unlimited-OCR — transformers

| sample | word-recall | meaning | exampleEn | exampleJa |
|---|---|---|---|---|
| IMG_4122 | 8/8 | 6/8 | 8/8 | 5/8 |
| IMG_4123 | 7/8 | 3/8 | 5/8 | 6/8 |
| IMG_4124 | 1/8 →(8/8) | 0/8 →(6/8) | 1/8 →(7/8) | 0/8 →(1/8) |
| IMG_4125 | 8/8 | 5/8 | 8/8 | 6/8 |
| section-11 | 8/8 | 7/8 | 8/8 | 2/8 |
| **合計(再試行込)** | **39/40** | **27/40** | **36/40** | **20/40** |

- IMG_4124 は既定設定（gundam: 640px+crop）で「欢迎光临…」の無限繰り返し（968秒、124KB）。base設定（1024px, crop無効, max_length=8192）で復旧。

### 総合比較

| 指標 | Tesseract単独 | DeepSeek-OCR (v1/Ollama) | DeepSeek-OCR-2 | Unlimited-OCR |
|---|---|---|---|---|
| 見出し語 (word-recall) | 21/40 | **40/40** | **40/40** | 39/40 |
| 日本語の意味 | 0% | 8/40 | **28/40** | 27/40 |
| 英語例文 | 0% | 36/40 | **38/40** | 36/40 |
| 日本語訳 | 0% | 3/40 | 15/40 | **20/40** |
| 繰り返しループ | — | **0/5** | 1/5 | 1/5 |
| 1枚あたり時間 | — | **9〜20秒** | 31〜130秒 | 32〜52秒 |

## 所見

1. **見出し語と英語例文は3モデルともほぼ完璧**。Tesseract（21/40）から劇的に改善。
2. **日本語の忠実な転写は transformers 系2モデル（v2 / Unlimited）が明確に優位**。v1/Ollamaは日本語欄を「読んで要約・翻訳し直す」挙動が強く、中国語混入も多いため、原文どおりの抽出用途には不向き。
3. **v1/Ollamaは速度と安定性が突出**（9〜20秒、ループゼロ、セットアップも`ollama pull`のみ）。Ollama側で画像が縮小されている可能性が高く、細かい日本語が潰れていることが精度低下の一因とみられる。
4. **v2とUnlimitedは5枚中1枚で繰り返しループが発生**。設定変更（crop無効・解像度変更）で復旧可能だが、実運用ではループ検知＋リトライが必須。
5. 右端の細い日本語訳列は全モデル苦手。スマホ写真の画質限界であり、撮影品質改善か辞書補正の併用が現実的。

## 結論・推奨

- **全フィールド（意味・日本語訳含む）を原文どおり抽出したい場合**: baidu/Unlimited-OCR または DeepSeek-OCR-2（僅差でUnlimited推奨。日本語訳列の取得率と速度の安定性で優位）。`max_length=8192` 制限＋反復検知リトライのガードを入れること。
- **見出し語＋英語例文だけ取れればよい場合（日本語は辞書補正で補完する構成）**: **DeepSeek-OCR (v1) + Ollama が最有力**。word-recall 40/40・ループなし・1枚10秒前後・導入が`ollama pull`一発と、運用コストが圧倒的に低い。既存アプリの辞書補正（`detectKnownPageCards`）と組み合わせれば実用構成になる。
- 日本語欄の抽出精度がどうしても必要なら、撮影をスキャンアプリ経由にして画質を上げるのが最も効く。

## 生成物

- `results/deepseek-ocr-v1-ollama/<name>/result.md`（Ollama出力）
- `results/deepseek-ocr-2/<name>/result.mmd`（+ ループした IMG_4125 は `IMG_4125-freeocr/`, `IMG_4125-nocrop/`）
- `results/unlimited-ocr/<name>/result.md`（+ `IMG_4124-base/`）
- transformers系は各フォルダの `result_with_boxes.jpg` に検出ボックス可視化

## 再現手順

### DeepSeek-OCR (v1) — Ollama

```powershell
ollama pull deepseek-ocr
python scripts\ollama_ocr.py samples\ocr results\deepseek-ocr-v1-ollama
```

### transformers系（venv×2、モデルごとにtransformersのバージョンが異なる）

```powershell
# DeepSeek-OCR-2 用
uv venv ds-env --python 3.12
uv pip install --python ds-env\Scripts\python.exe torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu126
uv pip install --python ds-env\Scripts\python.exe transformers==4.46.3 tokenizers==0.20.3 einops addict easydict pillow

# Unlimited-OCR 用
uv venv baidu-env --python 3.12
uv pip install --python baidu-env\Scripts\python.exe torch==2.10.0 torchvision --index-url https://download.pytorch.org/whl/cu128
uv pip install --python baidu-env\Scripts\python.exe transformers==4.57.1 einops addict easydict pillow matplotlib

# 推論（初回はモデル約7GBを自動ダウンロード）
ds-env\Scripts\python.exe scripts\run_ocr_bench.py --model deepseek --images samples\ocr --out results\deepseek-ocr-2
baidu-env\Scripts\python.exe scripts\run_ocr_bench.py --model baidu --images samples\ocr --out results\unlimited-ocr

# 採点
ds-env\Scripts\python.exe scripts\eval_ocr.py samples\ocr-expected results\deepseek-ocr-2
```

モデルは `AutoModel.from_pretrained(repo, trust_remote_code=True, torch_dtype=torch.bfloat16, _attn_implementation="eager")` でロードし、`model.infer(...)` を呼ぶ（flash-attn不要）。
