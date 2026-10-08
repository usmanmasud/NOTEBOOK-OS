# Deploying NotebookOS on Huawei Cloud

> **Status:** this runbook and the files in [`deploy/`](../deploy) have been prepared,
> and the same containers run locally with MySQL 8.4 and Redis 7. A deployment to a live
> Huawei Cloud account has **not** been performed yet. Record the outcome (URL and date)
> here once it has.

## Target architecture (what we deploy)

```
Internet ──HTTPS :443──▶ ECS (public EIP, security group: 80/443)
                          ├─ caddy     (HTTPS, automatic certificate; <ip>.sslip.io works without a domain)
                          ├─ frontend  (nginx: React app, /api proxy)
                          ├─ backend   (FastAPI, uvicorn)  ──VPC :3306──▶ RDS for MySQL (no public IP)
                          ├─ redis     (sessions, OTP, rate limits)
                          └─ uploads volume (notebook photos)
```

This is the compliant core: **the web app and API run on Huawei Cloud ECS and all
business data lives in Huawei Cloud RDS for MySQL.** Redis and photo storage run on the
ECS to keep setup short. Each can move to a managed service later without code changes
(`REDIS_URL` → DCS, `STORAGE_BACKEND=obs` → OBS); see sections 3–4.

**Quick path** (details in the numbered sections below):
1. VPC + security groups (section 1).
2. RDS for MySQL in the same VPC; database `notebookos` + user `notebookos` (section 2).
3. ECS (Ubuntu 22.04, 2 vCPU / 4 GB, with an EIP) in the same VPC, then on the ECS:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/usmanmasud/NOTEBOOK-OS/main/deploy/ecs-setup.sh | sudo sh
   sudo nano /opt/notebookos/deploy/.env.production   # DOMAIN, PUBLIC_BASE_URL, CORS_ORIGINS, DATABASE_URL
   sudo sh /opt/notebookos/deploy/start.sh
   ```
4. Open `https://<ip-with-dashes>.sslip.io` and run the demo.

## 1. Networking (VPC)

1. Create a **VPC** (for example `10.0.0.0/16`) with two subnets: `app` (ECS) and
   `data` (RDS, DCS).
2. Create security groups:
   * `sg-notebookos-web` (ECS): inbound 80 and 443 from anywhere; 22 only while you set up
     (or use the console's remote login).
   * `sg-notebookos-data` (RDS, and DCS if used): inbound **3306 (and 6379) from
     `sg-notebookos-web` only**. No public IPs.
   * (If you use an ELB instead of Caddy, the ECS only needs 8080 from the ELB.)
3. The ECS needs outbound internet (EIP or NAT gateway) to pull images and call the
   OCR/SIS/OBS endpoints.

## 2. RDS for MySQL

1. Create an **RDS for MySQL 8.0** instance in the `data` subnet with `sg-data`. Do not
   bind a public EIP.
2. Create the database `notebookos` (charset `utf8mb4`, collation `utf8mb4_unicode_ci`)
   and a dedicated account `notebookos` with privileges on that database only.
3. Set `DATABASE_URL=mysql+pymysql://notebookos:<password>@<rds-private-ip>:3306/notebookos?charset=utf8mb4`.
4. Enable automated backups.

## 3. DCS for Redis

1. Create a **DCS Redis 6/7** instance in the `data` subnet with `sg-data`, with password
   access enabled.
2. Set `REDIS_URL=redis://:<password>@<dcs-private-ip>:6379/0` (`rediss://` if SSL is enabled).

DCS holds sessions, OTP challenges and rate limits, so the app can run more than one
worker or ECS instance.

## 4. OBS

1. Create a bucket (for example `notebookos-uploads`) with **private** ACL and
   server-side encryption.
2. Create an IAM user with programmatic access, limited to that bucket (`obs:object:*`
   on the bucket).
3. Set `STORAGE_BACKEND=obs`, `OBS_ENDPOINT=https://obs.<region>.myhuaweicloud.com`,
   `OBS_REGION`, `OBS_BUCKET`, `OBS_ACCESS_KEY_ID` and `OBS_SECRET_ACCESS_KEY`.

Files are never served from public OBS URLs. The backend streams them to the owner
through `GET /api/uploads/{id}/file`.

## 5. AI services (optional, with offline fallback)

* **OCR:** enable Huawei Cloud OCR (handwriting) in the region. Create an IAM user with
  OCR permission, then set `HUAWEI_PROJECT_ID`, `HUAWEI_IAM_DOMAIN`, `HUAWEI_IAM_USER`,
  `HUAWEI_IAM_PASSWORD` and `OCR_PROVIDER=huawei,demo`.
* **Speech:** enable SIS, then set `SPEECH_PROVIDER=huawei,demo` and
  `HUAWEI_SIS_LANGUAGE`.
* **LLM:** for any OpenAI-compatible endpoint (for example ModelArts MaaS), set
  `LLM_PROVIDER=openai_compatible`, `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL`.
  Keep `LLM_FALLBACK_TO_RULES=true`.

These providers are implemented but have not been exercised against the live services.
Test them first with `curl https://<host>/api/health/dependencies` and an upload. If they
fail, the app falls back automatically, and the demo samples still work offline.

## 6. ECS and application deployment

1. Create an **ECS** instance (for example 2 vCPU / 4 GB, Ubuntu 22.04 or Huawei Cloud
   EulerOS) in the `app` subnet with `sg-app`.
2. Install Docker Engine and the compose plugin, then clone the repository.
3. Configure the environment:
   ```bash
   cp deploy/env.production.example deploy/.env.production
   chmod 600 deploy/.env.production      # holds secrets; never commit it
   vi deploy/.env.production
   ```
4. Build and start (also re-run this to deploy updates; it pulls the latest code):
   ```bash
   sudo sh /opt/notebookos/deploy/start.sh
   ```
   With `APP_ENV=production`, the backend **refuses to start** if `OTP_DEV_ECHO` is on,
   the database is SQLite, or `REDIS_URL` is missing.

## 7. HTTPS

Choose one option:

* **Recommended: Huawei ELB.** Create a shared or dedicated load balancer with an
  **HTTPS :443 listener** that uses a certificate from Huawei Cloud SCM (or an uploaded
  one). Point the backend server group at the ECS on port **8080**, and configure the
  health check as `HTTP GET /health`. Optionally add an HTTP :80 listener that redirects
  to HTTPS.
* **Single ECS with a public EIP:** point the domain's DNS at the EIP and start the
  bundled Caddy profile, which obtains a certificate automatically:
  ```bash
  DOMAIN=notebookos.example.com docker compose -f deploy/docker-compose.prod.yml \
    --env-file deploy/.env.production --profile caddy up -d
  ```
  In this case `sg-app` must allow 80 and 443 from the internet.

Set `PUBLIC_BASE_URL` and `CORS_ORIGINS` to the HTTPS origin so share links are correct.

## 8. Database migrations

Migrations run automatically on every backend start (`alembic upgrade head` in
`backend/entrypoint.sh`) after waiting for the database. To run them by hand:

```bash
docker compose -f deploy/docker-compose.prod.yml exec backend alembic upgrade head
```

With `DEMO_MODE=true` the entrypoint seeds the fictional demo account once, and it is
idempotent. Set `DEMO_MODE=false` for real traders.

## 9. Health checks

```bash
sh deploy/check.sh https://notebookos.example.com
```

* `GET /health` is a liveness check, used by the ELB and Docker.
* `GET /api/health/dependencies` reports the database, cache, storage and AI provider
  status. It returns `"status": "degraded"` if RDS, DCS or OBS is unreachable, and it
  never includes hosts or secrets.

## 10. Environment variables

See [`deploy/env.production.example`](../deploy/env.production.example) for the full
production list, and [`.env.example`](../.env.example) for descriptions. Secrets are only
ever provided as environment variables.

## Proving Huawei Cloud is the real infrastructure (for judges)

* Show the ECS console with the running instance, and `docker ps` on it.
* Show `GET /api/health/dependencies` from the public URL. It reports
  `"database": {"backend": "mysql"}`, `"cache": {"backend": "redis"}` and
  `"storage": {"backend": "obs"}`.
* Upload a photo, then show the new object in the OBS bucket and the new row in RDS
  (DAS console: `SELECT status, created_at FROM uploads ORDER BY created_at DESC LIMIT 1;`).

## Operations notes

* Logs: `docker compose … logs -f backend`. Pipeline events (`upload_received`,
  `processing_started`, `ocr_completed`, `ai_extraction_completed`,
  `validation_completed`, `human_confirmation`, `report_generated`) are single-line JSON
  and can be shipped to Huawei Cloud LTS with the ICAgent.
* Scaling: run more backend workers (`WEB_CONCURRENCY`) or more ECS instances behind the
  ELB. Sessions are in DCS, so any instance can serve any request.
