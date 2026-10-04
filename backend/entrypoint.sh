#!/bin/sh
# Apply migrations, optionally seed the fictional demo account, then serve.
set -e
python -m app.cli wait-for-db
alembic upgrade head
if [ "${DEMO_MODE:-true}" = "true" ]; then
  python -m app.cli seed-demo
fi
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "${WEB_CONCURRENCY:-2}" --proxy-headers --forwarded-allow-ips="*"
