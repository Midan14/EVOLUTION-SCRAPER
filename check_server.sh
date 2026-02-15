#!/bin/bash
# Script para verificar el estado del servidor y los servicios

SERVER="165.232.142.48"

echo "=== Verificando conectividad básica ==="
if ping -c 3 $SERVER > /dev/null 2>&1; then
    echo "✅ Servidor responde a ping"
else
    echo "❌ Servidor NO responde a ping"
    exit 1
fi

echo "=== Verificando SSH ==="
if nc -zv $SERVER 22 2>&1 | grep -q "succeeded"; then
    echo "✅ Puerto SSH (22) está abierto"
else
    echo "❌ Puerto SSH (22) NO está disponible"
    exit 1
fi

echo "=== Conectando al servidor ==="
ssh -o ConnectTimeout=10 root@$SERVER '
    echo "=== Estado del sistema ==="
    uptime
    df -h
    free -h
    
    echo "=== Estado de la VPN ==="
    systemctl is-active fastestvpn || echo "VPN no está activa"
    
    echo "=== Estado del bot ==="
    systemctl status dragonbot --no-pager
    
    echo "=== IP actual del servidor ==="
    curl -s --connect-timeout 5 ifconfig.me || echo "No se pudo obtener IP externa"
    
    echo "=== Últimos logs del bot ==="
    journalctl -u dragonbot -n 10 --no-pager
'