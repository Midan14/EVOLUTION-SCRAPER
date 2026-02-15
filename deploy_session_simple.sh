#!/bin/bash
# Script automático - subirá storage_state.json y reiniciará el bot
# Te pedirá la contraseña del servidor

set -e

SERVER="root@134.209.37.219"
REMOTE_PATH="/root/EVOLUTION-SCRAPER"

echo "🔄 PASO 1: Verificando storage_state.json..."
if [ ! -f "storage_state.json" ]; then
    echo "❌ storage_state.json no existe!"
    exit 1
fi

FILE_AGE=$(( $(date +%s) - $(stat -f %m storage_state.json) ))
echo "✅ storage_state.json tiene ${FILE_AGE} segundos"

echo ""
echo "📤 PASO 2: Subiendo y reiniciando..."
echo "   (Se te pedirá la contraseña del servidor 2 veces)"

# Subir archivo
scp storage_state.json ${SERVER}:${REMOTE_PATH}/ && \

# Reiniciar y mostrar logs (todo en un solo comando SSH)
ssh ${SERVER} "systemctl restart dragonbot && sleep 15 && journalctl -u dragonbot -n 50 --no-pager"

echo ""
echo "✅ ¡Listo!"
echo ""
echo "🔍 Para monitoreo continuo:"
echo "   ssh ${SERVER} 'journalctl -u dragonbot -f'"
