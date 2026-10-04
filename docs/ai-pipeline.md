# AI pipeline

The pipeline has four explicit stages. The first three run in `app/services/pipeline.py`
and the fourth in `app/analytics/metrics.py`.

| Stage | Input → output | Code |
|---|---|---|
| **READ** | photo / audio / text → lines with confidence and bounding boxes | `app/providers/*`, `registry.read_image` / `transcribe` |
| **UNDERSTAND** | lines → candidate records (strict schema) | `app/extraction/*` |
| **VALIDATE** | candidates → issues + review status | `app/validation/rules.py` |
| **SUMMARIZE** | confirmed records → metrics | `app/analytics/metrics.py` |

## READ

Providers implement small protocols in `app/providers/base.py`:

```python
class OCRProvider(Protocol):
    def read_image(self, data: bytes, mime_type: str) -> ReadResult: ...
class SpeechProvider(Protocol):
    def transcribe(self, data: bytes, mime_type: str) -> ReadResult: ...
class LLMProvider(Protocol):
    def complete_json(self, system: str, user: str) -> str: ...
```

Providers are configured as **chains** (`OCR_PROVIDER=huawei,demo`). Each provider is
tried in order, and a provider failure or crash moves on to the next. If every provider
fails, the upload is marked `FAILED` with a user-safe message, and the trader can retry
or enter transactions manually. The app never blocks on one external provider.

| Provider | Status |
|---|---|
| `HuaweiOCRProvider` | Huawei Cloud OCR `handwriting` (or `general-text`) API with IAM token auth. Parses `words_block_list` into lines with normalised bounding boxes. Response parsing is unit-tested; not yet run against the live service. |
| `HuaweiSpeechProvider` | Huawei Cloud SIS short-audio recognition (WAV/MP3). Not yet run against the live service. |
| `DemoOCRProvider` / `DemoSpeechProvider` | Offline. They recognise only the bundled fictional samples (by SHA-256) and return their pre-recorded reading. Results are flagged `is_fixture` and the UI shows *Demo reading (offline)*. Any other file is reported as unavailable, never guessed. |
| typed text | Each line becomes a source line with confidence 1.0 |

## UNDERSTAND

Two interchangeable interpreters produce the same `Candidate` structure.

### LLM interpreter (`llm_interpreter.py`)

* Works with any OpenAI-compatible chat endpoint (e.g. Huawei Cloud ModelArts MaaS).
* Each input line is tagged with an id such as `[p2:L3]`. **The model must attach every
  record to one of those ids.** Provenance (`page-2-row-4`, bounding box, original text)
  is then assigned by application code from that id, never by the model. A record that
  cites an unknown id is discarded.
* The output is validated against a strict Pydantic schema (`LLMOutput`): known types
  only, and confidence between 0 and 1. Any JSON or schema error rejects the whole
  response, and the pipeline falls back to the rule-based interpreter
  (`LLM_FALLBACK_TO_RULES=true`). The fallback reason is stored and shown in the UI.
* Prompt rules: never invent values; use `null` when unclear; do no arithmetic; treat
  written totals separately.

### Rule-based interpreter (`rules.py`)

A deterministic, offline reader driven by **vocabulary packs**
(`app/extraction/vocab/en.json`, `ha.json`). Adding a language or market means adding a
JSON file and listing it in `EXTRACTION_LANGUAGES`. No code changes are needed.

* Type keywords are matched as whole words, longest first, without overlaps. Composite
  phrasings resolve sensibly: *ya biya bashi* is a repayment, *sold … on credit* is a debt.
* Amounts: `20k`, `₦20,000`, `N2,500`, `1.5m`, `dubu 15` / `15 dubu`. Digits that OCR
  commonly confuses (`8,5OO`) are read but given low confidence. A `?` (`2?`, `?,000`)
  makes the value **null**.
* Quantities come from unit words in either order (`3 bags`, `buhu 2`).
* People are the leading capitalised words that carry no vocabulary meaning.
* Items are canonical names from the vocab (`shinkafa` → Rice), and expenses map to
  categories (`kudin mota` → Transport).
* A date heading applies to the lines below it. Lines with *total/jimla* become written
  totals.

### Confidence

Each field gets its own confidence. A record's confidence is the minimum over its
**required** fields (`type`, `amount`, plus `person` for debts and repayments), capped by
the OCR confidence of the source line. A smudged line read at 61% therefore can never
produce a 90% record.

## VALIDATE

Validation is deterministic, never rejects anything automatically, and produces issues:

| Severity | Examples | Effect |
|---|---|---|
| `error` | missing type or amount, amount ≤ 0, debt/repayment without a person | Blocks confirmation until fixed |
| `warning` | field confidence below `CONFIDENCE_REVIEW`, amount above `SUSPICIOUS_AMOUNT`, future or very old date, **AI amount or name not found in the original text** | Highlighted for review |

* Confidence levels: `high ≥ CONFIDENCE_HIGH (0.85)`, `review ≥ CONFIDENCE_REVIEW (0.60)`,
  otherwise `low`. Both thresholds are configurable.
* **Written-total check:** when a page has a written total, it is compared with the sum
  of extracted cash sales on that page, and a mismatch is shown (*"a line may be missing
  or misread"*).
* The *not-in-source* check is how LLM hallucinations get caught. It is skipped for
  values the trader typed.

## Human confirmation

Only an explicit human action (`POST /records/{id}/confirm` or
`POST /uploads/{id}/confirm`) sets `CONFIRMED`. The AI's original proposal is stored in
`ai_original`, and edits are recorded as `human_fields`, so the evidence view can say
*"Quantity corrected by trader (AI read: unclear)"*.

## SUMMARIZE

`compute_metrics()` is a pure function over confirmed records, using `Decimal`
arithmetic:

| Metric | Definition |
|---|---|
| Total Sales | Σ SALE |
| Credit Given | Σ DEBT |
| Debt Collected | Σ PAYMENT |
| Outstanding Debt | Σ over people of max(DEBT − PAYMENT, 0) |
| Expenses | Σ EXPENSE |
| Stock Purchases | Σ RESTOCK |
| Net Cash Flow | Sales + Debt Collected − Expenses − Stock Purchases |
| Stock movement | per item: RESTOCK quantity in, SALE+DEBT quantity out |

An LLM may optionally re-phrase the report narrative, which is first written from a
template. The rewrite is **rejected if it contains any number that is not already in
the calculated text** (`reports/builder.py::llm_narrative`).

*Patterns* (unusually high expense, older unpaid credit, credit rising while
collections fall) are simple explainable rules. They are labelled *"Pattern detected"*,
never "risk" or "fraud".

## Accuracy

The automated tests check the behaviour on realistic **fictional** lines. No accuracy
figure on real traders' notebooks has been measured, and none is claimed.
