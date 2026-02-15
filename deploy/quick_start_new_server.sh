#!/usr/bin/env bash
# Script de inicio rápido para nuevo servidor
# Ejecuta este script DESPUÉS de crear el droplet en DigitalOcean
# Uso: bash deploy/quick_start_new_server.sh

set -euo pipefail

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     CONFIGURACIÓN RÁPIDA - SERVIDOR NUEVO                  ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Leer IP del servidor
read -p "🔹 Ingresa la IP del NUEVO servidor: " SERVER_IP

if [[ -z "$SERVER_IP" ]]; then
    echo "❌ ERROR: No ingresaste una IP"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "PASO 1: Verificar conexión SSH"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if ssh -o ConnectTimeout=10 -o BatchMode=yes root@$SERVER_IP exit 2>/dev/null; then
    echo "✅ Conexión SSH exitosa (con clave SSH)"
else
    echo "⚠️  Intentando conectar (puede pedir contraseña)..."
    if ! ssh -o ConnectTimeout=10 root@$SERVER_IP 'echo "Conectado"'; then
        echo "❌ ERROR: No se puede conectar al servidor"
        echo "   Verifica:"
        echo "   - Que la IP sea correcta: $SERVER_IP"
        echo "   - Que el droplet esté encendido en DigitalOcean"
        echo "   - Que tengas la contraseña o clave SSH correcta"
        exit 1
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "PASO 2: Actualizar IP en archivos del proyecto"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

read -p "¿Actualizar la IP en los archivos del proyecto? [S/n] " update_ip
if [[ ! "$update_ip" =~ ^[nN]$ ]]; then
    # Actualizar IP en archivos
    OLD_IP="165.232.142.48"
    
    FILES=(
        "deploy/README.md"
        "deploy/diagnose_server.sh"
        "deploy/deploy_from_mac.sh"
        "deploy/check_server_status.sh"
        "digitalocean_logs_guide.md"
        "TROUBLESHOOTING_SERVIDOR.md"
    )
    
    for file in "${FILES[@]}"; do
        if [[ -f "$file" ]]; then
            sed -i '' "s/$OLD_IP/$SERVER_IP/g" "$file" 2>/dev/null || sed -i "s/$OLD_IP/$SERVER_IP/g" "$file"
            echo "  ✅ Actualizado: $file"
        fi
    done
    echo ""
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "PASO 3: Subir código al servidor"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

REMOTE_DIR="/root/EVOLUTION-SCRAPER"

echo "📤 Subiendo archivos..."
if rsync -avz --delete \
  --exclude 'venv' \
  --exclude 'browser_data' \
  --exclude '.env' \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.mypy_cache' \
  --exclude 'logs/*.log' \
  ./ root@$SERVER_IP:$REMOTE_DIR/; then
    echo "✅ Código subido exitosamente"
else
    echo "❌ ERROR al subir archivos"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "PASO 4: Configurar .env en el servidor"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [[ -f ".env" ]]; then
    read -p "¿Copiar archivo .env al servidor? [S/n] " copy_env
    if [[ ! "$copy_env" =~ ^[nN]$ ]]; then
        if scp .env root@$SERVER_IP:$REMOTE_DIR/; then
            echo "✅ Archivo .env copiado"
        else
            echo "❌ ERROR al copiar .env"
        fi
    fi
else
    echo "⚠️  No se encontró archivo .env en tu Mac"
    echo "   Deberás crear uno en el servidor manualmente"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "PASO 5: Ejecutar setup en el servidor"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

read -p "¿Ejecutar setup ahora? (instala PostgreSQL, Python, Playwright) [S/n] " run_setup
if [[ ! "$run_setup" =~ ^[nN]$ ]]; then
    echo "⏳ Ejecutando setup (esto puede tardar 5-10 minutos)..."
    echo ""
    
    if ssh root@$SERVER_IP "cd $REMOTE_DIR && PROJECT_DIR=$REMOTE_DIR bash deploy/do_setup.sh"; then
        echo ""
        echo "✅ Setup completado"
    else
        echo ""
        echo "⚠️  Setup tuvo problemas - revisa los errores arriba"
        echo "   Puedes intentar de nuevo manualmente:"
        echo "   ssh root@$SERVER_IP 'cd $REMOTE_DIR && PROJECT_DIR=$REMOTE_DIR bash deploy/do_setup.sh'"
    fi
fi

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║     CONFIGURACIÓN INICIAL COMPLETA                         ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📋 PRÓXIMOS PASOS MANUALES:"
echo ""
echo "1️⃣  Configurar VPN (Colombia):"
echo "   Sigue las instrucciones en: deploy/VPN_COLOMBIA.md"
echo ""
echo "2️⃣  Hacer login en el casino (en tu Mac):"
echo "   python save_storage_state.py"
echo "   touch storage_state.ready"
echo "   scp storage_state.json root@$SERVER_IP:$REMOTE_DIR/"
echo ""
echo "3️⃣  Instalar y activar el bot:"
echo "   ssh root@$SERVER_IP"
echo "   cp $REMOTE_DIR/deploy/dragonbot.service /etc/systemd/system/"
echo "   systemctl daemon-reload"
echo "   systemctl enable dragonbot"
echo "   systemctl start dragonbot"
echo "   systemctl status dragonbot"
echo ""
echo "📖 Guía completa: deploy/CREAR_SERVIDOR_NUEVO.md"
echo ""
