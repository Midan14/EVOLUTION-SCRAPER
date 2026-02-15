#!/bin/bash
# Deployment automático completo al servidor de producción
# Incluye: código + storage_state.json fresco + reinicio

set -e

SERVER="root@134.209.37.219"
REMOTE_PATH="/root/EVOLUTION-SCRAPER"

echo "═══════════════════════════════════════════════════════════"
echo "🚀 DEPLOYMENT AUTOMÁTICO A PRODUCCIÓN"
echo "═══════════════════════════════════════════════════════════"
echo ""

echo "📋 PASO 1: Verificando archivos locales..."
if [ ! -f "dragon_bot_ml.py" ]; then
    echo "❌ dragon_bot_ml.py no existe!"
    exit 1
fi

if [ ! -f "storage_state.json" ]; then
    echo "❌ storage_state.json no existe!"
    exit 1
fi

FILE_AGE=$(( $(date +%s) - $(stat -f %m storage_state.json) ))
echo "✅ dragon_bot_ml.py OK"
echo "✅ storage_state.json OK (${FILE_AGE}s de antigüedad)"

if [ $FILE_AGE -gt 300 ]; then
    echo "⚠️  ADVERTENCIA: storage_state.json tiene más de 5 minutos"
    echo "   Puede estar expirado. Considera regenerarlo."
    read -p "¿Continuar de todos modos? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Deployment cancelado"
        exit 1
    fi
fi

echo ""
echo "📤 PASO 2: Subiendo archivos al servidor..."
echo "   (Se te pedirá la contraseña 2 veces)"
echo ""

# Subir código actualizado
scp dragon_bot_ml.py ${SERVER}:${REMOTE_PATH}/ && \

# Subir storage_state fresco
scp storage_state.json ${SERVER}:${REMOTE_PATH}/ && \

# Reiniciar y verificar
ssh ${SERVER} "
echo '🔄 Reiniciando bot...'
systemctl restart dragonbot
echo '⏳ Esperando 20 segundos...'
sleep 20
echo ''
echo '📊 LOGS MÁS RECIENTES:'
echo '═══════════════════════════════════════════════════════════'
journalctl -u dragonbot -n 60 --no-pager
"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ DEPLOYMENT COMPLETADO"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "🔍 Busca en los logs arriba:"
echo "   ✅ '✅ WebSocket activo sin Lightning visible'"
echo "   ✅ '✅ WebSocket del juego conectado'"
echo "   ✅ '🎮 Nueva ronda'"
echo ""
echo "📊 Para monitoreo en vivo:"
echo "   ssh ${SERVER} 'journalctl -u dragonbot -f'"
echo ""
