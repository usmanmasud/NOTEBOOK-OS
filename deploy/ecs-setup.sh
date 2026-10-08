#!/bin/sh
# First-time setup on a fresh Huawei Cloud ECS (Ubuntu 22.04/24.04).
#
#   curl -fsSL https://raw.githubusercontent.com/usmanmasud/NOTEBOOK-OS/main/deploy/ecs-setup.sh | sudo sh
#
# Installs Docker, clones (or updates) the repository into /opt/notebookos and creates
# deploy/.env.production from the template. It does not start the app: fill in the
# CHANGE_ME values first, then run deploy/start.sh.
set -e

REPO="${REPO:-https://github.com/usmanmasud/NOTEBOOK-OS.git}"
DIR=/opt/notebookos

if ! command -v docker >/dev/null 2>&1; then
  echo ">> Installing Docker"
  apt-get update -y
  apt-get install -y ca-certificates curl git
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker

if [ -d "$DIR/.git" ]; then
  echo ">> Updating $DIR"
  git -C "$DIR" pull --ff-only
else
  echo ">> Cloning into $DIR"
  git clone "$REPO" "$DIR"
fi

ENV="$DIR/deploy/.env.production"
if [ ! -f "$ENV" ]; then
  cp "$DIR/deploy/env.production.example" "$ENV"
  chmod 600 "$ENV"
  echo ">> Created $ENV"
fi

PUBLIC_IP=$(curl -fsS --max-time 5 https://api.ipify.org || true)
echo
echo "Next:"
echo "  1. nano $ENV"
[ -n "$PUBLIC_IP" ] && echo "     Your public IP looks like $PUBLIC_IP -> DOMAIN=$(echo "$PUBLIC_IP" | tr . -).sslip.io"
echo "  2. sudo sh $DIR/deploy/start.sh"
