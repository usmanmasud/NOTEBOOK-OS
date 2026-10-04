# Security and privacy

This is a hackathon MVP with sensible baseline protections. **No regulatory compliance
(e.g. NDPA/GDPR) is claimed.**

## Authentication and sessions

* Phone + one-time code. Codes are random 6-digit values (`secrets`), stored only as
  **salted SHA-256 hashes** in Redis. They expire after 5 minutes, are single use, allow
  5 attempts, and are limited to 5 requests per phone per hour and 20 per IP per hour.
* **SMS delivery is not implemented.** In development the code can be echoed in the API
  response (`OTP_DEV_ECHO=true`), and production refuses to start with that setting. A
  real deployment must plug an SMS gateway (for example Huawei Cloud Message & SMS) into
  `app/auth/service.py::request_otp`.
* Sessions are 256-bit random bearer tokens. Only their SHA-256 hash is stored in
  Redis, with a 12-hour TTL by default. Logout deletes the session.
* The demo account is available only when `DEMO_MODE=true` and contains fictional data
  only.

## Authorization

* Every upload, record, file and report is checked against the session's user. Another
  user's resources return 404.
* IDs are random UUIDs.

## Uploads

* Type is detected from **file content (magic bytes)**, not the client's MIME type or
  extension.
* Size limits are 10 MB for photos and 15 MB for audio, enforced while reading.
* Filenames are reduced to a base name, and storage keys are server-generated
  (`uploads/<user>/<uuid>.<ext>`). The local storage backend rejects path traversal.
* Files are streamed back only through the authenticated API with `nosniff`. The OBS
  bucket stays private.
* Upload rate limit: 20 per minute per user.

## Shared reports

* Share tokens are `secrets.token_urlsafe(24)` (192 bits). They can't be guessed and can
  be revoked.
* The public endpoint returns only the frozen report snapshot. It excludes internal IDs,
  uploads, notebook images and **customer names** (debtors appear only as counts and
  totals).
* Revoked and unknown tokens return the same 404, and the endpoint is rate limited per IP.
* The trader must tick an explicit consent box before a report is generated: *"this
  report contains information from the records I confirmed…"*.
* Report wording states that it is a summary of confirmed user-provided records, **not
  a credit score**, and that NotebookOS does not verify the trader's finances.

## Secrets and configuration

* All secrets come from environment variables. `.env` files are git-ignored, and only
  `.env.example` templates are committed.
* `/api/health/dependencies` reports reachability only, never hosts or credentials.
* Production start-up fails on unsafe settings (dev OTP echo, SQLite, no Redis).
* OpenAPI docs are disabled in production.

## Network (production)

RDS and DCS live in a private subnet that only the app security group can reach. Public
traffic arrives via HTTPS at the ELB. See [deployment.md](deployment.md).

## Logging

Pipeline events are logged as structured JSON with IDs and counts. Codes, tokens,
passwords and keys are never logged; `log_event` also redacts keys with those names.
Phone numbers are masked in logs and API responses.

## Errors

A global exception handler returns a generic message and logs the full trace on the
server only. Provider failures are converted into fixed, user-safe messages. A test
checks that internal error details don't leak.

## Deletion

`DELETE /api/uploads/{id}` removes the stored file and every record derived from it.
The UI warns how many confirmed records this will remove. Account-level deletion
(delete the user and all their data) is not exposed in the UI yet. The database
cascades (`ON DELETE CASCADE` from `users`) make it a single-row delete, which is the
documented next step.

## Known gaps

* No SMS gateway (see above).
* There is no CSRF exposure, because auth uses a bearer header rather than cookies. The
  session token is kept in `localStorage`, so an XSS bug would expose it. React escaping
  and a strict nginx header set reduce that risk, and a Content-Security-Policy is a
  recommended next step.
* There is no malware scanning of uploads. They are never executed or served with an
  executable content type.
