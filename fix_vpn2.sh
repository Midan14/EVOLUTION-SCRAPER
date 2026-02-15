#!/bin/bash
# Script agresivo - intenta cada 1 segundo durante 3 minutos
echo "⏳ Intentando conectar cada 1 segundo..."
echo "Si ya hiciste Power Cycle, esto capturará la ventana"
echo ""

for i in $(seq 1 180); do
    result=$(ssh -o ConnectTimeout=2 -o StrictHostKeyChecking=no -o BatchMode=yes root@165.227.69.58 'systemctl stop fastestvpn 2>/dev/null; systemctl disable fastestvpn 2>/dev/null; echo DONE' 2>/dev/null)
    if echo "$result" | grep -q "DONE"; then
        echo ""
        echo "🎉 CONECTADO - VPN detenida!"
        exit 0
    fi
    printf "."
    sleep 1
done

echo ""
echo "⚠️ No se pudo conectar"
