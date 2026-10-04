# API reference

The base path is `/api`, except `/health`, which is also served at the root for load
balancers. Interactive OpenAPI docs are at `/api/docs` outside production.

Authenticated endpoints need `Authorization: Bearer <session token>`. Resources owned
by another user return **404**, not 403, so their existence isn't revealed. Errors
always have the shape `{"detail": "<user-safe message>"}`, and validation errors also
include `fields`. Stack traces are never returned.

## Health

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | `{"status": "ok"}` |
| GET | `/api/health/dependencies` | Database, cache, storage and AI provider status. No hosts or secrets. |

## Auth

| Method | Path | Body | Notes |
|---|---|---|---|
| POST | `/api/auth/request-otp` | `{phone}` | 6-digit code, 5 min TTL, 5 requests/hour/phone. `dev_code` is returned only when `OTP_DEV_ECHO=true` outside production. |
| POST | `/api/auth/verify-otp` | `{phone, code}` | → `{token, user}`. 5 attempts per code, single use. |
| POST | `/api/auth/demo` | – | Demo account session. Only when `DEMO_MODE=true`. |
| POST | `/api/auth/logout` | – | Ends the session |
| GET / PATCH | `/api/auth/me` | `{name?, business_name?}` | Profile. The phone number is masked. |

## Uploads (capture → READ/UNDERSTAND/VALIDATE)

| Method | Path | Notes |
|---|---|---|
| POST | `/api/uploads/photo` | multipart `file`. JPEG/PNG/WebP, checked by magic bytes, ≤ 10 MB. → **202** `PROCESSING` |
| POST | `/api/uploads/voice` | multipart `file`. WAV/MP3/M4A/OGG/WebM, ≤ 15 MB. → **202** |
| POST | `/api/uploads/text` | `{text}`. Typed fallback, one transaction per line. → **202** |
| GET | `/api/uploads` | Your uploads, newest first, with record counts per status |
| GET | `/api/uploads/{id}` | Status, `error_message`, `pipeline` (providers used, demo-fixture flag, written-total checks), `pages[].lines` (text, confidence, bbox) |
| GET | `/api/uploads/{id}/file` | Original photo/audio (authenticated stream) |
| GET | `/api/uploads/{id}/records` | Extracted records |
| POST | `/api/uploads/{id}/records` | Manual record (e.g. when reading failed) |
| POST | `/api/uploads/{id}/confirm` | `{record_ids?}` confirms all non-rejected records (or the listed ones). **422** lists the records with blocking errors. |
| POST | `/api/uploads/{id}/retry` | Re-run processing (not allowed once records are confirmed) |
| DELETE | `/api/uploads/{id}` | Deletes the file and all records from it → `{deleted, records_removed}` |

Upload status: `UPLOADED → PROCESSING → REVIEW → CONFIRMED`, or `FAILED`. Poll
`GET /api/uploads/{id}` until it is no longer `PROCESSING`.

## Records (human in the loop)

| Method | Path | Notes |
|---|---|---|
| GET | `/api/records/{id}` | Record with provenance |
| PATCH | `/api/records/{id}` | Any of `date, type, item, quantity, amount, person, notes`. Amount accepts `"20k"`. The record is re-validated, and a confirmed record returns to review. |
| POST | `/api/records/{id}/confirm` | **422** if the record has blocking errors |
| POST | `/api/records/{id}/reject` | Excluded from all metrics |

A record looks like this (abridged):

```json
{
  "id": "4f0c…",
  "type": "DEBT", "amount": 20000, "person": "Musa", "item": "Rice", "quantity": 2, "date": "2026-10-01",
  "confidence": 0.61, "confidence_level": "review",
  "field_confidence": {"type": 0.9, "amount": 0.95, "person": 0.85, "quantity": 0.2},
  "validation_issues": [],
  "human_fields": ["quantity"], "edited": true,
  "ai_original": {"quantity": null, "amount": "20000", "...": "..."},
  "status": "CONFIRMED", "confirmed_at": "2026-10-04T22:44:10",
  "source": {
    "upload_id": "…", "upload_type": "PHOTO", "page_number": 2, "reference": "page-2-row-4",
    "original_text": "Musa shinkafa 2? 20k bashi",
    "bbox": {"x": 0.11, "y": 0.27, "width": 0.38, "height": 0.05},
    "has_image": true, "read_by": "demo-fixture", "read_is_demo_fixture": true,
    "interpreted_by": "rules", "seeded_demo_history": false
  }
}
```

## Dashboard and evidence (SUMMARIZE)

| Method | Path | Notes |
|---|---|---|
| GET | `/api/dashboard?start=&end=` | Metrics from **confirmed records only**, plus debtors, stock movement, items, trend, recent records, pending-review count and patterns |
| GET | `/api/dashboard/evidence/{metric}?person=` | The value, its formula, and every contributing confirmed record with provenance |

Metric keys: `total_sales`, `credit_given`, `debt_collected`, `outstanding_debt`,
`total_expenses`, `stock_purchases`, `net_cash_flow`, `transactions`.

## Reports

| Method | Path | Notes |
|---|---|---|
| POST | `/api/reports` | `{consent: true, period_start?, period_end?, title?}`. Without consent → 422. Returns `share_token` and `share_url`. |
| GET | `/api/reports` | Your reports |
| POST | `/api/reports/{id}/revoke` | The link stops working immediately |
| GET | `/api/reports/{share_token}` | **Public, read-only, no login.** Returns only the title, generation time and frozen snapshot: no internal IDs, uploads or customer names. Revoked and unknown tokens return the same 404. Rate limited per IP. |

The frontend renders shared reports at `/reports/{share_token}`.

## Client config and demo

| Method | Path | Notes |
|---|---|---|
| GET | `/api/config` | Currency, locale, languages, thresholds, provider names, upload limits |
| GET | `/api/demo/samples` | Fictional sample files (demo mode only) |
| GET | `/api/demo/samples/{id}/file` | Sample file bytes |
| POST | `/api/demo/reset` | `{with_history}`. Demo account only. |
