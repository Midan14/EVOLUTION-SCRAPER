#!/usr/bin/env bash
# Script de diagnóstico automático del servidor de producción
# Uso: bash deploy/diagnose_server.sh

SERVER="165.227.69.58"
USER="root"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     DIAGNÓSTICO AUTOMÁTICO - DRAGON BOT PRODUCCIÓN        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

echo "🔍 Servidor: $USER@$SERVER"
echo ""

# Verificar conexión SSH
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  VERIFICANDO CONEXIÓN SSH"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if ! ssh -o ConnectTimeout=10 -o BatchMode=yes $USER@$SERVER exit 2>/dev/null; then
    echo "❌ ERROR: No se puede conectar al servidor"
    echo "   Verifica tu conexión a Internet o las credenciales SSH"
    exit 1
fi
echo "✅ Conexión SSH exitosa"
echo ""

# Estado del servicio DragonBot
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  ESTADO DEL SERVICIO DRAGONBOT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
BOT_STATUS=$(ssh $USER@$SERVER 'systemctl is-active dragonbot' 2>/dev/null || echo "error")
if [ "$BOT_STATUS" = "active" ]; then
    echo "✅ El servicio está ACTIVO"
    ssh $USER@$SERVER 'systemctl status dragonbot --no-pager | head -15'
elif [ "$BOT_STATUS" = "failed" ]; then
    echo "❌ El servicio está FALLIDO"
    ssh $USER@$SERVER 'systemctl status dragonbot --no-pager | head -15'
else
    echo "⚠️  El servicio está: $BOT_STATUS"
    ssh $USER@$SERVER 'systemctl status dragonbot --no-pager | head -15'
fi
echo ""

# PostgreSQL
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  ESTADO DE POSTGRESQL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
PG_STATUS=$(ssh $USER@$SERVER 'systemctl is-active postgresql' 2>/dev/null || echo "error")
if [ "$PG_STATUS" = "active" ]; then
    echo "✅ PostgreSQL está ACTIVO"
else
    echo "❌ PostgreSQL está: $PG_STATUS"
fi
echo ""

# VPN
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4️⃣  ESTADO DEL VPN (FastestVPN)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
VPN_STATUS=$(ssh $USER@$SERVER 'systemctl is-active fastestvpn 2>/dev/null || echo "not-found"')
if [ "$VPN_STATUS" = "active" ]; then
    echo "✅ VPN está ACTIVO"
elif [ "$VPN_STATUS" = "not-found" ]; then
    echo "⚠️  VPN no está instalado o configurado"
else
    echo "❌ VPN está: $VPN_STATUS"
fi

echo ""
echo "📍 IP actual del servidor:"
CURRENT_IP=$(ssh $USER@$SERVER 'curl -s --max-time 5 ifconfig.me 2>/dev/null || echo "Error obteniendo IP"')
echo "   $CURRENT_IP"
echo ""

# Archivos importantes
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5️⃣  VERIFICANDO ARCHIVOS CRÍTICOS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# .env
if ssh $USER@$SERVER '[ -f /root/EVOLUTION-SCRAPER/.env ]'; then
    echo "✅ Archivo .env existe"
else
    echo "❌ Archivo .env NO existe"
fi

# storage_state.json
if ssh $USER@$SERVER '[ -f /root/EVOLUTION-SCRAPER/storage_state.json ]'; then
    STORAGE_AGE=$(ssh $USER@$SERVER 'stat -c %Y /root/EVOLUTION-SCRAPER/storage_state.json 2>/dev/null || echo 0')
    NOW=$(date +%s)
    AGE_DAYS=$(( ($NOW - $STORAGE_AGE) / 86400 ))
    if [ $AGE_DAYS -gt 7 ]; then
        echo "⚠️  storage_state.json existe pero tiene $AGE_DAYS días (puede estar expirado)"
    else
        echo "✅ storage_state.json existe ($AGE_DAYS días)"
    fi
else
    echo "❌ storage_state.json NO existe"
fi

# dragon_bot_ml.py
if ssh $USER@$SERVER '[ -f /root/EVOLUTION-SCRAPER/dragon_bot_ml.py ]'; then
    echo "✅ dragon_bot_ml.py existe"
else
    echo "❌ dragon_bot_ml.py NO existe"
fi

# venv
if ssh $USER@$SERVER '[ -d /root/EVOLUTION-SCRAPER/venv ]'; then
    echo "✅ Virtual environment existe"
else
    echo "❌ Virtual environment NO existe"
fi
echo ""

# Últimos logs
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6️⃣  ÚLTIMOS 30 LOGS DEL BOT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ssh $USER@$SERVER 'journalctl -u dragonbot -n 30 --no-pager 2>/dev/null' || echo "⚠️  No se pueden leer logs"
echo ""

# Errores críticos en logs
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7️⃣  ERRORES CRÍTICOS EN LOGS (últimas 500 líneas)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ERROR_COUNT=$(ssh $USER@$SERVER 'journalctl -u dragonbot -n 500 --no-pager 2>/dev/null | grep -c -i "error\|failed\|exception\|traceback" || echo 0')
if [ "$ERROR_COUNT" -gt 0 ]; then
    echo "⚠️  Encontrados $ERROR_COUNT errores en los últimos logs:"
    echo ""
    ssh $USER@$SERVER 'journalctl -u dragonbot -n 500 --no-pager 2>/dev/null | grep -i "error\|failed\|exception" | tail -10'
else
    echo "✅ No se encontraron errores recientes"
fi
echo ""

# Uso de recursos
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "8️⃣  USO DE RECURSOS DEL SERVIDOR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ssh $USER@$SERVER 'free -h && echo "" && df -h / && echo "" && uptime'
echo ""

# Resumen y recomendaciones
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "9️⃣  RESUMEN Y RECOMENDACIONES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ISSUES=0

if [ "$BOT_STATUS" != "active" ]; then
    echo "🔴 CRÍTICO: El bot NO está corriendo"
    echo "   → Solución: bash deploy/fix_server.sh restart"
    ISSUES=$((ISSUES + 1))
fi

if [ "$PG_STATUS" != "active" ]; then
    echo "🔴 CRÍTICO: PostgreSQL NO está corriendo"
    echo "   → Solución: ssh root@$SERVER 'systemctl start postgresql'"
    ISSUES=$((ISSUES + 1))
fi

if [ "$VPN_STATUS" != "active" ] && [ "$VPN_STATUS" != "not-found" ]; then
    echo "🟡 ADVERTENCIA: VPN no está activo (el casino podría bloquear el acceso)"
    echo "   → Solución: ssh root@$SERVER 'systemctl start fastestvpn'"
    ISSUES=$((ISSUES + 1))
fi

if ! ssh $USER@$SERVER '[ -f /root/EVOLUTION-SCRAPER/storage_state.json ]'; then
    echo "🟡 ADVERTENCIA: No existe storage_state.json (sesión del casino)"
    echo "   → Solución: Generar nuevo storage_state.json desde tu Mac"
    ISSUES=$((ISSUES + 1))
elif [ "${AGE_DAYS:-0}" -gt 7 ]; then
    echo "🟡 ADVERTENCIA: storage_state.json tiene $AGE_DAYS días (probablemente expirado)"
    echo "   → Solución: Generar nuevo storage_state.json desde tu Mac"
    ISSUES=$((ISSUES + 1))
fi

if [ "$ERROR_COUNT" -gt 10 ]; then
    echo "🟡 ADVERTENCIA: Muchos errores en logs ($ERROR_COUNT)"
    echo "   → Revisa los logs completos: ssh root@$SERVER 'journalctl -u dragonbot -n 100'"
    ISSUES=$((ISSUES + 1))
fi

if [ $ISSUES -eq 0 ]; then
    echo "✅ No se detectaron problemas críticos"
    echo ""
    echo "Si el bot sigue sin funcionar, verifica:"
    echo "  1. Que el casino no haya cambiado su estructura web"
    echo "  2. Que la sesión (storage_state.json) siga válida"
    echo "  3. Los logs completos: ssh root@$SERVER 'journalctl -u dragonbot -f'"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              DIAGNÓSTICO COMPLETADO                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
