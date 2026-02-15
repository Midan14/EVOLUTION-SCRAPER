#!/bin/bash
# 🚀 DEPLOYMENT COMPLETO: Código + Session + VPN
# Este script configura TODO en el nuevo servidor automáticamente

set -e

SERVER="root@134.209.37.219"
REMOTE_PATH="/root/EVOLUTION-SCRAPER"

echo "═══════════════════════════════════════════════════════════"
echo "🚀 DEPLOYMENT COMPLETO CON VPN"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}⚠️  IMPORTANTE: Necesitas las credenciales de FastestVPN${NC}"
echo ""
read -p "Usuario FastestVPN: " VPN_USER
read -sp "Contraseña FastestVPN: " VPN_PASS
echo ""
echo ""

echo "📋 PASO 1: Verificando archivos locales..."
if [ ! -f "dragon_bot_ml.py" ] || [ ! -f "storage_state.json" ]; then
    echo -e "${RED}❌ Archivos faltantes!${NC}"
    exit 1
fi

FILE_AGE=$(( $(date +%s) - $(stat -f %m storage_state.json) ))
echo -e "${GREEN}✅ Archivos OK (storage_state: ${FILE_AGE}s)${NC}"

if [ $FILE_AGE -gt 600 ]; then
    echo -e "${YELLOW}⚠️  storage_state tiene >10min. Puede estar expirado.${NC}"
fi

echo ""
echo "📤 PASO 2: Subiendo archivos al servidor..."

# Subir archivos principales
scp dragon_bot_ml.py storage_state.json ${SERVER}:${REMOTE_PATH}/ || {
    echo -e "${RED}❌ Error subiendo archivos${NC}"
    exit 1
}

echo -e "${GREEN}✅ Archivos subidos${NC}"

echo ""
echo "🔧 PASO 3: Configurando FastestVPN..."

ssh ${SERVER} bash <<ENDSSH
set -e

echo "📦 Instalando OpenVPN..."
apt update -qq && apt install -y openvpn unzip wget curl > /dev/null 2>&1

echo "📥 Descargando configs de FastestVPN..."
cd /root
if [ ! -f "fastestvpn_ovpn.zip" ]; then
    wget -q "https://support.fastestvpn.com/download/fastestvpn_ovpn/" -O fastestvpn_ovpn.zip 2>/dev/null || {
        echo "⚠️  No se pudo descargar. Usa configs existentes o sube el zip manualmente."
    }
fi

if [ -f "fastestvpn_ovpn.zip" ]; then
    echo "📂 Extrayendo configs..."
    unzip -o -q fastestvpn_ovpn.zip
    
    echo "🔍 Buscando config de Colombia..."
    # Buscar archivo de Colombia (tcp preferido)
    COLOMBIA_FILE=\$(find /root -name "*.ovpn" -path "*/tcp/*" | xargs grep -l -i "colombia" 2>/dev/null | head -1)
    
    if [ -z "\$COLOMBIA_FILE" ]; then
        # Intentar udp si no hay tcp
        COLOMBIA_FILE=\$(find /root -name "*.ovpn" | xargs grep -l -i "colombia" 2>/dev/null | head -1)
    fi
    
    if [ -n "\$COLOMBIA_FILE" ]; then
        echo "✅ Encontrado: \$COLOMBIA_FILE"
        cp "\$COLOMBIA_FILE" /root/fastestvpn-colombia.ovpn
    else
        echo "❌ No se encontró config de Colombia"
        exit 1
    fi
else
    if [ ! -f "/root/fastestvpn-colombia.ovpn" ]; then
        echo "❌ No hay config de VPN disponible"
        exit 1
    fi
    echo "✅ Usando config existente"
fi

echo "🔐 Configurando autenticación..."
cat > /root/fastestvpn.auth <<EOF
$VPN_USER
$VPN_PASS
EOF
chmod 600 /root/fastestvpn.auth

# Agregar auth-user-pass si no existe
if ! grep -q "auth-user-pass" /root/fastestvpn-colombia.ovpn; then
    echo "auth-user-pass /root/fastestvpn.auth" >> /root/fastestvpn-colombia.ovpn
fi

# Asegurar que redirija todo el tráfico
if ! grep -q "redirect-gateway" /root/fastestvpn-colombia.ovpn; then
    echo "redirect-gateway def1" >> /root/fastestvpn-colombia.ovpn
fi

echo "📝 Creando servicio systemd..."
cat > /etc/systemd/system/fastestvpn.service <<'EOFSERVICE'
[Unit]
Description=FastestVPN Colombia
After=network.target
Before=dragonbot.service

[Service]
Type=simple
ExecStart=/usr/sbin/openvpn --config /root/fastestvpn-colombia.ovpn
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOFSERVICE

systemctl daemon-reload
systemctl enable fastestvpn
systemctl stop fastestvpn 2>/dev/null || true
systemctl start fastestvpn

echo "⏳ Esperando 15s para que VPN conecte..."
sleep 15

echo "🌐 Verificando IP..."
ORIGINAL_IP=\$(curl -s --max-time 5 ifconfig.me 2>/dev/null || echo "unknown")
echo "IP actual: \$ORIGINAL_IP"

if systemctl is-active --quiet fastestvpn; then
    echo "✅ VPN activa"
else
    echo "⚠️  VPN no está activa, verificando logs..."
    journalctl -u fastestvpn -n 20 --no-pager
fi

ENDSSH

echo ""
echo "🔄 PASO 4: Reiniciando DragonBot..."

ssh ${SERVER} "systemctl restart dragonbot && sleep 20 && journalctl -u dragonbot -n 60 --no-pager"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ DEPLOYMENT COMPLETADO${NC}"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "🔍 Verifica en los logs arriba:"
echo "   ✅ '✅ WebSocket activo sin Lightning visible'"
echo "   ✅ '✅ WebSocket del juego conectado'"
echo "   ✅ '🎮 Nueva ronda'"
echo ""
echo "📊 Comandos útiles:"
echo "   ssh ${SERVER} 'systemctl status fastestvpn'  # Ver VPN"
echo "   ssh ${SERVER} 'curl ifconfig.me'             # Ver IP"
echo "   ssh ${SERVER} 'journalctl -u dragonbot -f'   # Logs bot"
echo ""
