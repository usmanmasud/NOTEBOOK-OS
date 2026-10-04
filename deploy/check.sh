#!/bin/sh
# Post-deployment smoke check:  sh deploy/check.sh https://notebookos.example.com
set -e
BASE="${1:-http://localhost:8080}"
echo "GET $BASE/health";                    curl -fsS "$BASE/health"; echo
echo "GET $BASE/api/health/dependencies";   curl -fsS "$BASE/api/health/dependencies"; echo
echo "GET $BASE/ (frontend)";               curl -fsS -o /dev/null -w "%{http_code}\n" "$BASE/"
