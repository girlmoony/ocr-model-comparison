# Honest Evaluation of the Tesseract-Only OCR Pipeline

> Note: This document evaluates the OCR pipeline of the original app (tango-quest-pwa). File paths such as `src/ocr.js` and `src/wordDatabase.js` refer to that app's repository, not this one.

Comparison against the expected JSON (`samples/ocr-expected/*.json`) of what the Tesseract OCR output alone produces when processed by `parseSegmentedOCR` / `parseFallbackOCR`, with dictionary correction (`detectKnownPageCards` in `wordDatabase.js`) turned **OFF**.

## Method

1. Split each `samples/ocr/*.{jpg,jpeg}` into 4 regions following `SPREAD_REGIONS` in `src/ocr.js`
2. Run each region through the Tesseract CLI and save the raw OCR text to `samples/ocr-results/<name>.raw.txt`
3. Process the same raw OCR text in two ways and save each as JSON:
   - `<name>.heuristic.json` : `parseOCRText(raw, { useDictionary: false })` … OCR only
   - `<name>.dictionary.json` : `parseOCRText(raw)` … with dictionary correction
4. Compare each field against the expected JSON and save to `<name>.diff.json`

## Aggregate Results

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

- **word-recall** … how many of the 8 expected headwords appear in the result (any order)
- **word-order** … whether the 8 expected headwords appear in the same order
- **exact-row** … number of rows where all 5 fields (`word/pronunciation/meaning/exampleEn/exampleJa`) match
- **field-acc** … percentage of matching fields out of 40 rows × 5 fields = 200 fields

## OCR-Only Headwords per Page (dictionary off)

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

## To Be Honest

### Quality of OCR only (heuristic)

- **field-acc = 0%** on all 5 pages … not a single row exactly matches the expected JSON.
- word-recall varies widely, 1/8 to 7/8. `section-11` recovers only 1/8.
- Even for headwords that are found, `pronunciation` only gets as far as wrapping the bracketed pronunciation like `[sopres]` in slashes `/…/`; proper IPA such as `/səprés/` never comes out.
- `meaning` fields are contaminated with fragments of other words' meanings and example sentences — unusable as-is for a vocabulary book.
- Large amounts of noise tokens (`opps`, `licj`, `fpipa`, `auelias`, etc.) inflate the card count beyond 8 to 9–11.

In other words, **with "Tesseract + the existing heuristic parser alone", you cannot expect photographed pages of similar-layout books to yield card rows the user can memorize from as-is.** It only works on the premise that the user fixes each row by hand in `EditCardsScreen` (in `src/App.jsx`).

### With dictionary correction (dictionary)

- All 5 pages perfect at 8/8.
- But that is because the correct data for these 5 pages is baked into `src/wordDatabase.js`. **Photograph a different page (Section 13 of the same book, or another book) and it will always fall back to OCR-only, since it's not in the dictionary.**

### Answer to "Will future photos of similar layouts all be recognized?"

- **Pages not in the dictionary**: the OCR-only numbers above are exactly what you get. 1–7 of 8 headwords hit; pronunciations, meanings, and examples are noisy. Acceptable as a rough starting point if the user edits by hand, but it cannot deliver an "automatic card creation" experience.
- **Pages in the dictionary**: 100% perfect.
- Ultimately the app's design (review and fix in `EditCardsScreen` before saving) is sound, and OCR plays the role of "drafting". As `readme_jp.md` itself says: *"OCR makes mistakes. Fix the word/meaning/examples here before saving."*

## How to Improve Quality from Here

If the goal is practical quality from OCR alone, the candidates are (in cost order):

1. **Extend the dictionary to the whole book**: register correct cards for the entire vocabulary book (a few thousand words) in `wordDatabase.js`, and every page of that book works at 100%. OCR then only needs to identify which headword it is, and aliases + example-sentence phrases are enough even with heavy noise.
2. **Switch OCR engines**: Tesseract 4 → Tesseract 5, or Cloud Vision / Apple Vision. If constrained to tesseract.js for fully on-device processing, the current setup is close to the ceiling.
3. **Strengthen preprocessing**: `enhance: true` (binarization + local mean correction) is already applied in `SPREAD_REGIONS`, but seriously operating the `parseStructuredCards` path — row detection (`detectCardRows`) combined with small-region OCR per each of the 8 rows — leaves room to improve headword recognition (currently `parseStructuredCards` requires CARD_NN_FIELD-format sections from the caller and never fires with plain text OCR).
4. **Fuzzy post-processing**: one-character errors and clipped edges (`hwispor` ↔ `whisper`, `posit` ↔ `deposit`) are common, so simply matching against an English word list in post-processing would raise the headword hit rate.

## Artifacts

| File | Contents |
|---|---|
| `samples/ocr-results/<name>.raw.txt` | Raw Tesseract OCR text for the 4 regions (delimited by `--- LABEL ---`) |
| `samples/ocr-results/<name>.heuristic.json` | `parseOCRText` output, OCR only (dictionary off) |
| `samples/ocr-results/<name>.dictionary.json` | `parseOCRText` output with dictionary on |
| `samples/ocr-results/<name>.diff.json` | Comparison metrics against expected JSON plus the actual card list |
| `samples/ocr-results/IMG_4122.raw.enhanced.txt` | Raw OCR of IMG_4122 re-taken with `enhance: true` preprocessing (reference) |

(These artifact paths refer to the original app repository.)
