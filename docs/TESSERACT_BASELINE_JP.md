# Tesseract OCR 単独パイプラインの正直な評価

辞書補正（`wordDatabase.js` の `detectKnownPageCards`）を **OFF** にして、Tesseract OCR の出力だけを `parseSegmentedOCR` / `parseFallbackOCR` で処理した結果と、期待 JSON（`samples/ocr-expected/*.json`）との比較です。

## 評価方法

1. `samples/ocr/*.{jpg,jpeg}` を `src/ocr.js` の `SPREAD_REGIONS` 通りに 4 領域へ分割
2. 各領域を Tesseract CLI に通して生 OCR テキストを `samples/ocr-results/<name>.raw.txt` に保存
3. 同じ生 OCR テキストを 2 通りで処理してそれぞれを JSON に保存
   - `<name>.heuristic.json` : `parseOCRText(raw, { useDictionary: false })` … OCR のみ
   - `<name>.dictionary.json` : `parseOCRText(raw)` … 辞書補正あり
4. 期待 JSON と項目ごとに突き合わせて `<name>.diff.json` に保存

## 集計結果

```
sample        mode        cards  word-recall  word-order  exact-row  field-acc
IMG_4122      heuristic    9/8     5/8          0/8         0/8         0%
IMG_4122      dictionary   8/8     8/8          8/8         8/8         100%
IMG_4123      heuristic    8/8     6/8          0/8         0/8         0%
IMG_4123      dictionary   8/8     8/8          8/8         8/8         100%
IMG_4124      heuristic   11/8     2/8          0/8         0/8         0%
IMG_4124      dictionary   8/8     8/8          8/8         8/8         100%
IMG_4125      heuristic   11/8     7/8          0/8         0/8         0%
IMG_4125      dictionary   8/8     8/8          8/8         8/8         100%
section-11    heuristic   10/8     1/8          0/8         0/8         0%
section-11    dictionary   8/8     8/8          8/8         8/8         100%

TOTAL heuristic   word-recall=21/40  word-order=0/40  exact-rows=0/40  field-acc=0%
TOTAL dictionary  word-recall=40/40  word-order=40/40  exact-rows=40/40  field-acc=100%
```

- **word-recall** … 期待 8 語のうち何語が結果に現れたか（順序問わず）
- **word-order** … 期待 8 語が同じ順序で現れたか
- **exact-row** … `word/pronunciation/meaning/exampleEn/exampleJa` の 5 項目すべて一致した行数
- **field-acc** … 合計 40 行 × 5 項目 = 200 フィールドのうち一致した割合

## 5 ページそれぞれの「OCR のみ」見出し語（dictionary off）

```
IMG_4122  expected : suppress, deceive, manipulate, starve, flee, whisper, yell, deposit
          heuristic: opps, suppress, deceive, manipulate, licj, starve, flee, posit, ider

IMG_4123  expected : confine, swing, prolong, depict, outline, shed, emit, renew
          heuristic: walking, confine, swing, prolong, depict, outline, shed, rene

IMG_4124  expected : plot, sculpture, tablet, dense, exotic, acid, bitter, sensible
          heuristic: more, svreez, plot, sculp, skalptfor, ablet, popu, exoti, acid, panacid, bitterly

IMG_4125  expected : slavery, prey, mess, recession, retreat, grave, column, scenery
          heuristic: forc, return, lunch, slavery, prey, mess, recession, retreat, jonze, grave, column

section-11 expected : exclude, overlook, burst, heal, forbid, install, diminish, cite
          heuristic: forbid, thas, shes, namic, passe, fpipa, auelias, ospod, urmin, seit
```

## 正直に言うと

### OCR のみ（heuristic）の品質

- 全 5 ページで **field-acc = 0%** … 期待 JSON と完全一致する行はゼロ。
- word-recall は 1/8 〜 7/8 でばらつきが大きい。`section-11` は 1/8 しか拾えていない。
- 拾えた見出し語でも `pronunciation` は `[sopres]` のように記号で囲まれた発音を `slashes /…/` に変換するに留まり、`/səprés/` のような IPA は出ない。
- `meaning` は他語の意味や例文の断片が混ざっていて、そのまま「単語帳」として使うのは無理。
- ノイズ語（`opps`, `licj`, `fpipa`, `auelias` 等）が大量に混入していて、`word-recall` の母数を 8 を超えて 9〜11 に膨らませている。

つまり **「Tesseract + 既存ヒューリスティックパーサ単独」では、将来似たレイアウトの本のページを撮影しても、ユーザーがそのまま暗記カードとして使えるカード列を期待することはできません**。ユーザーが `EditCardsScreen`（`src/App.jsx` 内）で 1 行ずつ手直しする前提でしか機能しません。

### 辞書補正（dictionary）あり

- 5 ページ全て 8/8 完璧。
- ただしこれは `src/wordDatabase.js` にこの 5 ページ分の正解データを焼き込んでいるからです。**別のページ（同じ単語帳の Section 13 や別の単語帳）を撮影すると、辞書にないので必ず OCR のみのフォールバックに落ちます**。

### 「将来似たレイアウトの撮影画像が全部認識できるか」への回答

- **辞書に登録されていないページ** : 上の OCR-only の数字がそのまま品質になります。8 語中 1〜7 語の見出し語ヒット、発音・意味・例文はノイズ混じり。ユーザーが手直し前提なら最低限の取っ掛かりにはなりますが、「自動でカードが作られる」体験は提供できません。
- **辞書に登録されているページ** : 100% 完璧。
- 結局アプリの設計（`EditCardsScreen` で確認・修正してから保存）は妥当で、OCR は「下書きを作る」役割。`readme_jp.md` にも *「OCRはミスります。ここで単語・意味・例文を直してから保存してください」* と書かれている通り。

## 今後品質を上げるには

OCR のみで実用品質を狙うのであれば、以下が候補です（コスト順）。

1. **辞書を本全体に拡張** : 単語帳 1 冊分（数千語）の正解カードを `wordDatabase.js` に登録すれば、その本に関しては全ページ 100% で動作します。OCR は「どの見出しか」を識別するだけになり、ノイズが多くてもエイリアス＋例文フレーズで十分。
2. **OCR エンジンを変える** : Tesseract 4 → Tesseract 5、または Cloud Vision / Apple Vision に置き換える。デバイス側で完結させたいので tesseract.js 縛りなら現状が天井に近い。
3. **前処理を強化** : 既に `enhance: true` を `SPREAD_REGIONS` に入れて二値化＋ローカル平均補正をかけてあるが、行検出（`detectCardRows`）と組み合わせて 8 行ごとに小領域 OCR をかける `parseStructuredCards` 経路を本気で運用すれば、見出し語の認識率は上がる余地があります（現状 `parseStructuredCards` は呼び出し側で CARD_NN_FIELD 形式のセクションが必要で、テキスト OCR 単独だと発火しません）。
4. **ファジー後処理** : 1 文字違い・前後カット (`hwispor` ↔ `whisper`、`posit` ↔ `deposit`) は十分にあり得るので、英単語辞書を持って後処理マッチングするだけでも見出し語ヒット率は上がる。

## 生成物一覧

| ファイル | 内容 |
|---|---|
| `samples/ocr-results/<name>.raw.txt` | 4 領域分の Tesseract 生 OCR テキスト（`--- LABEL ---` 区切り） |
| `samples/ocr-results/<name>.heuristic.json` | OCR のみ（辞書 off）の `parseOCRText` 出力 |
| `samples/ocr-results/<name>.dictionary.json` | 辞書 on の `parseOCRText` 出力 |
| `samples/ocr-results/<name>.diff.json` | 期待 JSON との比較メトリクスと実カード一覧 |
| `samples/ocr-results/IMG_4122.raw.enhanced.txt` | `enhance: true` で前処理した上で取り直した IMG_4122 の生 OCR（参考） |
