#!/usr/bin/env bash
# Script interactivo para actualizar la IP del servidor en todos los archivos
# Uso: bash deploy/update_server_ip.sh

set -euo pipefail

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     ACTUALIZAR IP DEL SERVIDOR EN EL PROYECTO              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

OLD_IP="165.227.69.58"

echo "📌 IP antigua del servidor: $OLD_IP"
echo ""
read -p "🔹 Ingresa la NUEVA IP del servidor: " NEW_IP

if [[ -z "$NEW_IP" ]]; then
    echo "❌ ERROR: No ingresaste una IP"
    exit 1
fi

# Validar formato básico de IP
if ! [[ "$NEW_IP" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "❌ ERROR: La IP '$NEW_IP' no parece válida"
    echo "   Formato esperado: XXX.XXX.XXX.XXX"
    exit 1
fi

echo ""
echo "🔍 Buscando archivos con la IP antigua..."
echo ""

# Archivos a actualizar
FILES=(
    "deploy/README.md"
    "deploy/diagnose_server.sh"
    "deploy/deploy_from_mac.sh"
    "deploy/check_server_status.sh"
    "digitalocean_logs_guide.md"
    "TROUBLESHOOTING_SERVIDOR.md"
)

FOUND=0
for file in "${FILES[@]}"; do
    if [[ -f "$file" ]] && grep -q "$OLD_IP" "$file" 2>/dev/null; then
        echo "  ✓ Encontrado en: $file"
        FOUND=$((FOUND + 1))
    fi
done

if [[ $FOUND -eq 0 ]]; then
    echo "  ℹ️  No se encontró la IP antigua en ningún archivo"
    echo ""
    read -p "¿Continuar de todas formas? [s/N] " confirm
    if [[ ! "$confirm" =~ ^[sS]$ ]]; then
        echo "❌ Operación cancelada"
        exit 0
    fi
fi

echo ""
echo "🔄 Actualizando IP de $OLD_IP → $NEW_IP"
echo ""

for file in "${FILES[@]}"; do
    if [[ -f "$file" ]]; then
        # Usar sed para reemplazar (compatible con macOS)
        sed -i '' "s/$OLD_IP/$NEW_IP/g" "$file" 2>/dev/null || sed -i "s/$OLD_IP/$NEW_IP/g" "$file"
        if grep -q "$NEW_IP" "$file"; then
            echo "  ✅ Actualizado: $file"
        fi
    else
        echo "  ⚠️  No existe: $file"
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ ACTUALIZACIÓN COMPLETA"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 PRÓXIMOS PASOS:"
echo ""
echo "1. Verifica la conexión SSH al nuevo servidor:"
echo "   ssh root@$NEW_IP"
echo ""
echo "2. Sube el proyecto al servidor:"
echo "   bash deploy/deploy_from_mac.sh"
echo ""
echo "3. Sigue la guía completa en:"
echo "   deploy/CREAR_SERVIDOR_NUEVO.md"
echo ""
