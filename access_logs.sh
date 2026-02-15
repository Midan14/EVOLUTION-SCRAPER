#!/bin/bash
# Script para acceder a logs del servidor con múltiples estrategias

SERVER="165.232.142.48"
USER="root"

echo "🔍 INTENTANDO ACCEDER A LOGS DEL SERVIDOR..."
echo "Servidor: $SERVER"
echo "================================"

# Función para intentar conexión
try_connection() {
    local method="$1"
    local command="$2"
    echo "📡 Método $method:"
    echo "Comando: $command"
    echo "--------------------------------"
    
    timeout 20 bash -c "$command" 2>&1 | head -20
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo "✅ Éxito con método $method"
        return 0
    elif [ $exit_code -eq 124 ]; then
        echo "⏰ Timeout en método $method"
    else
        echo "❌ Falló método $method (código: $exit_code)"
    fi
    return $exit_code
}

# Método 1: SSH directo a logs
echo "🔄 Intentando métodos de conexión..."
echo ""

try_connection "1-SSH-Directo" "ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no $USER@$SERVER 'journalctl -u dragonbot --no-pager -n 20'"
if [ $? -eq 0 ]; then exit 0; fi

echo ""

# Método 2: SSH con configuración alternativa
try_connection "2-SSH-Alt" "ssh -o ConnectTimeout=10 -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no $USER@$SERVER 'systemctl status dragonbot'"
if [ $? -eq 0 ]; then exit 0; fi

echo ""

# Método 3: Verificar si el servidor responde
try_connection "3-Ping" "ping -c 3 $SERVER"

echo ""

# Método 4: Verificar puerto SSH
try_connection "4-Port-Check" "nc -zv $SERVER 22"

echo ""
echo "🔍 DIAGNÓSTICO COMPLETO:"
echo "================================"

# Diagnóstico de red
echo "📡 Test de conectividad básica:"
ping -c 2 $SERVER 2>&1 | grep -E "(PING|transmitted|received)"

echo ""
echo "🔌 Test de puerto SSH:"
(echo > /dev/tcp/$SERVER/22) 2>/dev/null && echo "✅ Puerto 22 accesible" || echo "❌ Puerto 22 inaccesible"

echo ""
echo "💡 ALTERNATIVAS RECOMENDADAS:"
echo "1. 🌐 Panel DigitalOcean: https://cloud.digitalocean.com/"
echo "2. 💻 Consola web del droplet en el panel"
echo "3. 📱 Telegram: El bot está enviando estado en tiempo real"
echo "4. 🔄 VPN temporal: Desactivar FastestVPN para acceso SSH"
echo ""
echo "📋 Si necesitas logs específicos, el bot ya está enviando:"
echo "   - Estado de predicciones"
echo "   - Estadísticas de precisión" 
echo "   - Errores en tiempo real"
echo "   - Conexión al casino"