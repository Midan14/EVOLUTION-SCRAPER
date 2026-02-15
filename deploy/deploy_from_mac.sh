#!/usr/bin/env bash
# Sube el proyecto al servidor de producción y opcionalmente instala/reinicia el servicio.
# Uso: desde la raíz del proyecto:  bash deploy/deploy_from_mac.sh
# Requiere: rsync, ssh (clave o contraseña para root@165.232.142.48)

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVER="${DEPLOY_SERVER:-root@134.209.37.219}"
REMOTE_DIR="${REMOTE_DIR:-/root/EVOLUTION-SCRAPER}"

echo "==> Subiendo proyecto a $SERVER:$REMOTE_DIR"
rsync -avz --delete \
  --exclude 'venv' \
  --exclude 'browser_data' \
  --exclude '.env' \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.mypy_cache' \
  --exclude 'logs/*.log' \
  "$REPO_ROOT/" "$SERVER:$REMOTE_DIR/"

echo "==> Archivos subidos. En el servidor:"
echo "    1. Crea/edita .env (credenciales Telegram, casino)."
echo "    2. Opcional: copia storage_state.json desde tu Mac si ya hiciste login:"
echo "       scp $REPO_ROOT/storage_state.json $SERVER:$REMOTE_DIR/"
echo "    3. Si es la primera vez, ejecuta el setup:"
echo "       ssh $SERVER 'cd $REMOTE_DIR && PROJECT_DIR=$REMOTE_DIR bash deploy/do_setup.sh'"
echo "    4. Instala el servicio y arranca (24/7):"
echo "       ssh $SERVER 'sudo cp $REMOTE_DIR/deploy/dragonbot.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable dragonbot && sudo systemctl restart dragonbot && sudo systemctl status dragonbot'"
echo ""
read -r -p "¿Ejecutar ahora paso 4 (instalar/reiniciar servicio)? [s/N] " r
r_lc="$(printf '%s' "$r" | tr '[:upper:]' '[:lower:]')"
if [[ "$r_lc" == s || "$r_lc" == y ]]; then
  ssh "$SERVER" "sudo cp $REMOTE_DIR/deploy/dragonbot.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable dragonbot && sudo systemctl restart dragonbot && sudo systemctl status dragonbot"
fi
