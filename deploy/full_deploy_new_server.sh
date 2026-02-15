#!/usr/bin/env bash
# Script de deployment completo y automatizado al nuevo servidor
# Uso: bash deploy/full_deploy_new_server.sh

set -euo pipefail

NEW_SERVER="134.209.37.219"
USER="root"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║   DEPLOYMENT COMPLETO - NUEVO SERVIDOR DRAGON BOT          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "🎯 Servidor: $USER@$NEW_SERVER"
echo "📁 Proyecto: $REPO_ROOT"
echo ""

# Verificar archivos críticos locales
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  VERIFICANDO ARCHIVOS LOCALES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ ! -f "$REPO_ROOT/.env" ]; then
    echo "❌ ERROR: No existe $REPO_ROOT/.env"
    exit 1
fi
echo "✅ .env existe"

if [ ! -f "$REPO_ROOT/storage_state.json" ]; then
    echo "⚠️  ADVERTENCIA: No existe storage_state.json (el bot necesitará login manual)"
else
    echo "✅ storage_state.json existe"
fi

if [ ! -f "$REPO_ROOT/dragon_bot_ml.py" ]; then
    echo "❌ ERROR: No existe dragon_bot_ml.py"
    exit 1
fi
echo "✅ dragon_bot_ml.py existe"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  VERIFICANDO CONEXIÓN AL SERVIDOR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if ! ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$USER@$NEW_SERVER" 'echo "SSH_OK"' 2>/dev/null; then
    echo "❌ ERROR: No se puede conectar por SSH a $NEW_SERVER"
    echo ""
    echo "Verifica que:"
    echo "  - El servidor esté encendido"
    echo "  - Tengas la contraseña o SSH key configurada"
    echo "  - Puedes conectar manualmente: ssh root@$NEW_SERVER"
    exit 1
fi
echo "✅ Conexión SSH exitosa"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  SUBIENDO CÓDIGO AL SERVIDOR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

rsync -avz --delete \
  --exclude 'venv' \
  --exclude 'browser_data' \
  --exclude '.env' \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.mypy_cache' \
  --exclude 'logs/*.log' \
  --exclude 'ws_samples' \
  "$REPO_ROOT/" "$USER@$NEW_SERVER:/root/EVOLUTION-SCRAPER/"

echo "✅ Código subido"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4️⃣  SUBIENDO .ENV Y STORAGE_STATE.JSON"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

scp "$REPO_ROOT/.env" "$USER@$NEW_SERVER:/root/EVOLUTION-SCRAPER/"
echo "✅ .env subido"

if [ -f "$REPO_ROOT/storage_state.json" ]; then
    scp "$REPO_ROOT/storage_state.json" "$USER@$NEW_SERVER:/root/EVOLUTION-SCRAPER/"
    echo "✅ storage_state.json subido"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5️⃣  INSTALANDO DEPENDENCIAS EN EL SERVIDOR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⏳ Esto puede tomar 5-10 minutos..."
echo ""

ssh "$USER@$NEW_SERVER" bash <<'ENDSSH'
set -euo pipefail
cd /root/EVOLUTION-SCRAPER

echo "📦 Actualizando sistema..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3-venv python3-pip git libpq-dev postgresql postgresql-contrib wget curl > /dev/null 2>&1

echo "🗄️  Configurando PostgreSQL..."
systemctl enable postgresql > /dev/null 2>&1
systemctl start postgresql > /dev/null 2>&1

# Crear base de datos y usuario
sudo -u postgres psql -c "CREATE DATABASE dragon_bot;" 2>/dev/null || true
sudo -u postgres psql -c "CREATE USER root WITH PASSWORD 'DragonBotRoot2026!';" 2>/dev/null || \
  sudo -u postgres psql -c "ALTER USER root WITH PASSWORD 'DragonBotRoot2026!';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE dragon_bot TO root;" || true
sudo -u postgres psql -d dragon_bot -c "GRANT ALL ON SCHEMA public TO root;" 2>/dev/null || true

echo "🐍 Creando entorno virtual Python..."
python3 -m venv venv
source venv/bin/activate

echo "📚 Instalando dependencias Python..."
pip install --quiet --upgrade pip > /dev/null 2>&1
if [ -f requirements.txt ]; then
  pip install --quiet -r requirements.txt > /dev/null 2>&1
fi
pip install --quiet asyncpg playwright pandas numpy scikit-learn python-telegram-bot > /dev/null 2>&1

echo "🎭 Instalando Playwright Chromium..."
playwright install chromium --with-deps > /dev/null 2>&1

echo "✅ Instalación completa"
ENDSSH

echo "✅ Dependencias instaladas"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6️⃣  INSTALANDO SERVICIO SYSTEMD"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ssh "$USER@$NEW_SERVER" bash <<'ENDSSH'
cp /root/EVOLUTION-SCRAPER/deploy/dragonbot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable dragonbot
ENDSSH

echo "✅ Servicio instalado"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7️⃣  INICIANDO BOT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ssh "$USER@$NEW_SERVER" 'systemctl start dragonbot'
sleep 5

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "8️⃣  VERIFICANDO ESTADO"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ssh "$USER@$NEW_SERVER" 'systemctl status dragonbot --no-pager | head -15'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "9️⃣  ÚLTIMOS LOGS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ssh "$USER@$NEW_SERVER" 'journalctl -u dragonbot -n 30 --no-pager'

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              DEPLOYMENT COMPLETADO ✅                       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "🎉 El bot está corriendo en: $NEW_SERVER"
echo ""
echo "📋 Comandos útiles:"
echo ""
echo "  Ver logs en tiempo real:"
echo "    ssh root@$NEW_SERVER 'journalctl -u dragonbot -f'"
echo ""
echo "  Reiniciar bot:"
echo "    ssh root@$NEW_SERVER 'systemctl restart dragonbot'"
echo ""
echo "  Ver estado:"
echo "    ssh root@$NEW_SERVER 'systemctl status dragonbot'"
echo ""
echo "  Conectar al servidor:"
echo "    ssh root@$NEW_SERVER"
echo ""
