#!/bin/sh
# Build and (re)start NotebookOS on the ECS, then run the health checks.
#   sudo sh /opt/notebookos/deploy/start.sh
set -e
DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV="$DIR/deploy/.env.production"

if grep -q "CHANGE_ME" "$ENV"; then
  echo "!! $ENV still contains CHANGE_ME values:"
  grep -n "CHANGE_ME" "$ENV" | sed 's/=.*/=.../'
  exit 1
fi

git -C "$DIR" pull --ff-only || true
docker compose -f "$DIR/deploy/docker-compose.prod.yml" --env-file "$ENV" up -d --build

echo ">> Waiting for the backend (migrations run on start)..."
i=0
until docker compose -f "$DIR/deploy/docker-compose.prod.yml" --env-file "$ENV" exec -T backend \
    python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)" 2>/dev/null; do
  i=$((i+1)); [ $i -gt 60 ] && { echo "!! backend not healthy; logs:"; docker compose -f "$DIR/deploy/docker-compose.prod.yml" --env-file "$ENV" logs --tail 60 backend; exit 1; }
  sleep 3
done

DOMAIN=$(grep '^DOMAIN=' "$ENV" | cut -d= -f2)
echo ">> Backend healthy. Dependencies:"
docker compose -f "$DIR/deploy/docker-compose.prod.yml" --env-file "$ENV" exec -T backend \
  python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/health/dependencies').read().decode())"
echo
echo ">> Open https://$DOMAIN  (the HTTPS certificate can take up to a minute on first start)"
