#!/bin/bash
# Configurar FastestVPN Colombia y reiniciar el bot

SERVER="root@134.209.37.219"

echo "═══════════════════════════════════════════════════════════"
echo "🔐 CONFIGURAR FASTESTVPN COLOMBIA"
echo "═══════════════════════════════════════════════════════════"
echo ""

read -p "Usuario FastestVPN: " VPN_USER
read -sp "Contraseña FastestVPN: " VPN_PASS
echo ""
echo ""

echo "🔧 Configurando VPN en el servidor..."

ssh ${SERVER} bash <<ENDSSH
set -e

echo "📝 Copiando config de Colombia..."
cp /root/tcp_files/colombia-tcp.ovpn /root/fastestvpn-colombia.ovpn

echo "🔐 Creando archivo de autenticación..."
cat > /root/fastestvpn.auth <<EOF
${VPN_USER}
${VPN_PASS}
EOF
chmod 600 /root/fastestvpn.auth

echo "⚙️  Modificando config..."
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

echo "🔄 Habilitando e iniciando VPN..."
systemctl daemon-reload
systemctl enable fastestvpn
systemctl stop fastestvpn 2>/dev/null || true
systemctl start fastestvpn

echo "⏳ Esperando 15s para que VPN conecte..."
sleep 15

echo ""
echo "🌐 Verificando conexión VPN..."
echo "═══════════════════════════════════════════════════════════"

# Verificar estado del servicio
if systemctl is-active --quiet fastestvpn; then
    echo "✅ Servicio VPN: ACTIVO"
else
    echo "❌ Servicio VPN: INACTIVO"
    systemctl status fastestvpn --no-pager
fi

# Verificar IP
echo ""
NEW_IP=\$(curl -s --max-time 10 ifconfig.me 2>/dev/null || echo "error")
if [ "\$NEW_IP" != "134.209.37.219" ] && [ "\$NEW_IP" != "error" ]; then
    echo "✅ IP actual: \$NEW_IP (VPN funcionando)"
else
    echo "⚠️  IP actual: \$NEW_IP (puede que VPN no esté activa)"
    echo ""
    echo "📋 Últimos logs de VPN:"
    journalctl -u fastestvpn -n 20 --no-pager
fi

echo ""
echo "═══════════════════════════════════════════════════════════"

ENDSSH

echo ""
echo "🔄 Reiniciando DragonBot..."
echo ""

ssh ${SERVER} "systemctl restart dragonbot && sleep 20 && journalctl -u dragonbot -n 60 --no-pager"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ CONFIGURACIÓN COMPLETA"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "🔍 Verifica en los logs arriba:"
echo "   ✅ '✅ WebSocket activo sin Lightning visible'"
echo "   ✅ '✅ WebSocket del juego conectado'"
echo "   ✅ '🎮 Nueva ronda'"
echo ""
echo "📊 Comandos útiles:"
echo "   ssh ${SERVER} 'systemctl status fastestvpn'  # Estado VPN"
echo "   ssh ${SERVER} 'curl ifconfig.me'             # Ver IP actual"
echo "   ssh ${SERVER} 'journalctl -u dragonbot -f'   # Logs bot en vivo"
echo ""
