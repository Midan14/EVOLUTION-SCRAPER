#!/usr/bin/env bash
# Arranca el Dragon Bot con la ruta de Chromium del venv (evita "Executable doesn't exist")
cd "$(dirname "$0")"
VENV_BROWSERS="$(pwd)/venv/lib/python3.9/site-packages/playwright/driver/package/.local-browsers"
if [ -z "${PLAYWRIGHT_BROWSERS_PATH}" ] && [ -d "$VENV_BROWSERS" ]; then
  export PLAYWRIGHT_BROWSERS_PATH="$VENV_BROWSERS"
fi
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi
exec ./venv/bin/python dragon_bot_ml.py
