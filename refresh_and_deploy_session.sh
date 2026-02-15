#!/bin/bash
# Script para regenerar storage_state.json y subirlo inmediatamente al servidor

set -e

SERVER="root@134.209.37.219"
REMOTE_PATH="/root/EVOLUTION-SCRAPER"

echo "🔄 PASO 1: Verificando que storage_state.json existe y es reciente..."

if [ ! -f "storage_state.json" ]; then
    echo "❌ storage_state.json no existe!"
    echo "📝 Genera uno nuevo con: python save_storage_state.py"
    exit 1
fi

# Verificar que el archivo tiene menos de 5 minutos
FILE_AGE=$(( $(date +%s) - $(stat -f %m storage_state.json 2>/dev/null || stat -c %Y storage_state.json) ))
if [ $FILE_AGE -gt 300 ]; then
    echo "⚠️ storage_state.json tiene más de 5 minutos (${FILE_AGE}s)"
    echo "❌ Probablemente expiró. Regenera uno nuevo con: python save_storage_state.py"
    exit 1
fi

echo "✅ storage_state.json tiene ${FILE_AGE} segundos (fresco)"

echo ""
echo "📤 PASO 2: Subiendo storage_state.json al servidor..."
scp storage_state.json ${SERVER}:${REMOTE_PATH}/

echo ""
echo "📤 PASO 3: Verificando que se subió correctamente..."
ssh ${SERVER} "ls -lh ${REMOTE_PATH}/storage_state.json"

echo ""
echo "🔄 PASO 4: Reiniciando el bot..."
ssh ${SERVER} "systemctl restart dragonbot"

echo ""
echo "⏳ PASO 5: Esperando 15 segundos para que arranque..."
sleep 15

echo ""
echo "📊 PASO 6: Mostrando logs..."
ssh ${SERVER} "journalctl -u dragonbot -n 50 --no-pager"

echo ""
echo "✅ ¡Listo! Verifica en los logs si ahora funciona."
echo ""
echo "🔍 Para monitoreo continuo:"
echo "   ssh ${SERVER} 'journalctl -u dragonbot -f'"
