#!/usr/bin/env bash
# Script unificado para diagnosticar el servidor de producción
# Se conecta a la IP correcta del servidor

# Detectar IP del servidor desde deploy_from_mac.sh o usar default
SERVER_IP="${SERVER_IP:-165.227.69.58}"
USER="root"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     DIAGNÓSTICO SERVIDOR DRAGON BOT                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "🎯 Intentando conectar a: $USER@$SERVER_IP"
echo ""

# Test de conectividad básica
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  TEST DE CONECTIVIDAD"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if ping -c 3 -W 5 "$SERVER_IP" >/dev/null 2>&1; then
    echo "✅ El servidor responde a PING"
else
    echo "❌ El servidor NO responde a PING"
fi

echo ""
echo "Probando conexión SSH..."
if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$USER@$SERVER_IP" 'echo "SSH OK"' 2>/dev/null; then
    echo "✅ Conexión SSH funciona"
    echo ""
    
    # Si SSH funciona, ejecutar diagnóstico completo
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "2️⃣  ESTADO DEL BOT"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ssh "$USER@$SERVER_IP" 'systemctl status dragonbot --no-pager' || echo "⚠️ Servicio dragonbot no encontrado"
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "3️⃣  ÚLTIMOS LOGS"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ssh "$USER@$SERVER_IP" 'journalctl -u dragonbot -n 30 --no-pager' 2>/dev/null || echo "⚠️ No hay logs disponibles"
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "4️⃣  SERVICIOS DEPENDIENTES"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ssh "$USER@$SERVER_IP" 'systemctl is-active postgresql' 2>/dev/null && echo "✅ PostgreSQL activo" || echo "❌ PostgreSQL no activo"
    ssh "$USER@$SERVER_IP" 'systemctl is-active fastestvpn 2>/dev/null' && echo "✅ VPN activo" || echo "⚠️ VPN no activo/configurado"
    
else
    echo "❌ NO SE PUEDE CONECTAR POR SSH"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "POSIBLES CAUSAS:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "1. 🔴 El servidor está APAGADO"
    echo "   → Ve a https://cloud.digitalocean.com/droplets"
    echo "   → Busca el droplet con IP: $SERVER_IP"
    echo "   → Si está OFF, enciéndelo (Power On)"
    echo ""
    echo "2. 🔴 El servidor fue ELIMINADO"
    echo "   → Verifica en DigitalOcean si existe el droplet"
    echo "   → Si no existe, necesitas crear uno nuevo"
    echo ""
    echo "3. 🟡 Firewall bloqueando SSH"
    echo "   → En DigitalOcean: Networking → Firewalls"
    echo "   → Verifica que puerto 22 esté abierto"
    echo ""
    echo "4. 🟡 Red local bloqueando conexión"
    echo "   → Intenta desde otra red WiFi"
    echo "   → Usa VPN o datos móviles"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "SOLUCIÓN RÁPIDA:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "1. Ve a DigitalOcean: https://cloud.digitalocean.com/droplets"
    echo ""
    echo "2. Busca tu droplet con IP: $SERVER_IP"
    echo ""
    echo "3. Haz click en el droplet → \"Console\" o \"Access\""
    echo ""
    echo "4. Ejecuta estos comandos en la consola web:"
    echo "   systemctl status dragonbot"
    echo "   journalctl -u dragonbot -n 50"
    echo ""
fi

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              DIAGNÓSTICO COMPLETADO                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
