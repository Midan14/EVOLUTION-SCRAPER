#!/bin/bash
echo "⏳ Esperando que el servidor arranque..."
echo "HAZ POWER CYCLE EN DIGITALOCEAN AHORA"
echo ""

for i in $(seq 1 60); do
    result=$(ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no root@165.227.69.58 'systemctl stop fastestvpn; systemctl disable fastestvpn; echo OK' 2>/dev/null)
    if [ "$result" = "OK" ]; then
        echo ""
        echo "🎉 CONECTADO - VPN detenida y deshabilitada!"
        exit 0
    fi
    printf "."
    sleep 2
done

echo ""
echo "⚠️ No se pudo conectar en 2 minutos"
