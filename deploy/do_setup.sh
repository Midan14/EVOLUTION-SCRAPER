#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$HOME/EVOLUTION-SCRAPER}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "==> Instalando dependencias del sistema"
sudo apt update
sudo apt install -y \
  python3-venv python3-pip git \
  libpq-dev postgresql postgresql-contrib \
  wget curl

echo "==> Preparando base de datos"
sudo systemctl enable postgresql
sudo systemctl start postgresql
sudo -u postgres createdb dragon_bot || true
# Usuario para el servicio (dragonbot.service corre como root y usa postgresql://root:...)
sudo -u postgres psql -c "CREATE USER root WITH PASSWORD 'DragonBotRoot2026!';" 2>/dev/null || \
  sudo -u postgres psql -c "ALTER USER root WITH PASSWORD 'DragonBotRoot2026!';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE dragon_bot TO root;" || true
sudo -u postgres psql -d dragon_bot -c "GRANT ALL ON SCHEMA public TO root;" 2>/dev/null || true

echo "==> Preparando entorno Python"
cd "$PROJECT_DIR"
"$PYTHON_BIN" -m venv venv
source venv/bin/activate
pip install --upgrade pip

if [ -f requirements.txt ]; then
  pip install -r requirements.txt
fi

pip install asyncpg playwright pandas numpy scikit-learn python-telegram-bot
playwright install chromium --with-deps

echo "==> Listo. Ahora configura systemd con deploy/dragonbot.service"
