# DeepSeek-OCR-2 vs baidu/Unlimited-OCR ローカルGPU検証レポート

実施日: 2026-07-06 / 環境: RTX 4060 Ti (8GB), Windows 11, Python 3.12 (uv venv), CUDA版 PyTorch

`samples/ocr/` の5枚（単語帳の見開き写真）を両モデルでOCRし、`samples/ocr-expected/*.json` と照合した。

## 実行構成

| | DeepSeek-OCR-2 | baidu/Unlimited-OCR |
|---|---|---|
| パラメータ数 | 約3.4B (BF16) | 約3.3B (BF16) |
| torch / transformers | 2.6.0+cu126 / 4.46.3 | 2.10.0+cu128 / 4.57.1 |
| attention | eager（flash-attnはWindows未対応のため） | eager |
| プロンプト | `<image>\n<|grounding|>Convert the document to markdown. ` | `<image>document parsing.` |
| 基本設定 | base_size=1024, image_size=768, crop_mode=True | base_size=1024, image_size=640, crop_mode=True |
| ピークVRAM | 8.16 GB（共有メモリに一部溢れつつ動作） | 8.09 GB |
| 1枚あたり時間 | 31〜130秒 | 32〜52秒（暴走時968秒） |

## 精度（期待JSONとの照合、fuzzy一致しきい値0.85）

各画像8エントリ × 5枚 = 40エントリ。`()` は暴走した画像を代替設定で再実行した値。

### DeepSeek-OCR-2

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

### baidu/Unlimited-OCR

| sample | word-recall | meaning | exampleEn | exampleJa |
|---|---|---|---|---|
| IMG_4122 | 8/8 | 6/8 | 8/8 | 5/8 |
| IMG_4123 | 7/8 | 3/8 | 5/8 | 6/8 |
| IMG_4124 | 1/8 →(8/8) | 0/8 →(6/8) | 1/8 →(7/8) | 0/8 →(1/8) |
| IMG_4125 | 8/8 | 5/8 | 8/8 | 6/8 |
| section-11 | 8/8 | 7/8 | 8/8 | 2/8 |
| **合計(再試行込)** | **39/40** | **27/40** | **36/40** | **20/40** |

- IMG_4124 は既定設定（gundam: 640px+crop）で「欢迎光临…」の無限繰り返し（968秒、124KB）。base設定（1024px, crop無効, max_length=8192）で復旧。

### 参考: 既存Tesseractパイプライン（辞書補正OFF、HONEST_EVALUATION_JP.mdより）

word-recall **21/40**、フィールド一致 0% — 両VLMが圧倒的に上回る。

## 所見

1. **見出し語と英語例文はどちらもほぼ完璧**（word 39〜40/40、exampleEn 36〜38/40）。Tesseractの21/40から劇的に改善。辞書補正なしでカード生成が成立するレベル。
2. **日本語の意味欄は両者7割前後**。誤字パターンは「飢える→凱える」「餓死→幾死」（DeepSeek）、「操る→探る」「書類→雪類」（Unlimited）など、写真のブレ由来の類字誤認。
3. **日本語訳（右端の細い列）は両者とも弱い**（15〜20/40）。完全欠落（DeepSeek/section-11）か文字化けが多い。Unlimitedの方が列自体は拾う率が高い。
4. **両モデルとも5枚中1枚で繰り返しループが発生**（DeepSeek: IMG_4125 / Unlimited: IMG_4124）。設定変更（crop無効・解像度変更）で復旧可能だが、実運用ではリトライ機構が必須。
5. **速度はUnlimitedが安定して速い**（32〜52秒 vs DeepSeekの31〜130秒）。8GB VRAMでは両者ともギリギリ（ピーク約8.1GB、一部共有メモリへ溢れ）。

## 結論・推奨

- 総合精度はほぼ互角（DeepSeekは英文がわずかに強く、Unlimitedは日本語訳列の取得率と速度で優位）。
- **どちらか選ぶなら baidu/Unlimited-OCR をわずかに推奨**：既定で日本語訳列を拾いやすく、成功時の処理時間が安定して短い。ただし暴走時のダメージが大きい（968秒）ため `max_length` を8192程度に制限し、出力に同一文字列の反復を検知したら base設定で1回リトライするガードを入れること。
- ループ検知＋設定変更リトライを入れれば、どちらのモデルでも見出し語・英例文は辞書補正なしで実用水準。日本語訳はスマホ写真の画質では限界があり、撮影品質改善（スキャンアプリ利用）か既存の辞書補正の併用が現実的。

## 生成物

- `samples/ocr-results/deepseek-ocr-2/<name>/result.mmd`（+ ループした IMG_4125 は `IMG_4125-freeocr/`, `IMG_4125-nocrop/`）
- `samples/ocr-results/unlimited-ocr/<name>/result.md`（+ `IMG_4124-base/`）
- 各フォルダの `result_with_boxes.jpg` に検出ボックス可視化

## 再現手順（venvはセッション一時領域のため要再構築）

```powershell
uv venv ds-env --python 3.12
uv pip install --python ds-env\Scripts\python.exe torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu126
uv pip install --python ds-env\Scripts\python.exe transformers==4.46.3 tokenizers==0.20.3 einops addict easydict pillow

uv venv baidu-env --python 3.12
uv pip install --python baidu-env\Scripts\python.exe torch==2.10.0 torchvision --index-url https://download.pytorch.org/whl/cu128
uv pip install --python baidu-env\Scripts\python.exe transformers==4.57.1 einops addict easydict pillow matplotlib
```

モデルは `AutoModel.from_pretrained(repo, trust_remote_code=True, torch_dtype=torch.bfloat16, _attn_implementation="eager")` でロードし、`model.infer(tokenizer, prompt=..., image_file=..., output_path=..., base_size=1024, image_size=768/640, crop_mode=True)` を呼ぶ（flash-attn不要）。
