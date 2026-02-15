#!/bin/bash
# Script alternativo para conectar cuando VPN está activa

SERVER="165.232.142.48"

echo "=== Intentando conexión SSH con diferentes configuraciones ==="

# Intento 1: SSH standard
echo "Intento 1: SSH directo"
timeout 15 ssh -o ConnectTimeout=10 root@$SERVER 'echo "Conectado exitosamente"' && exit 0

# Intento 2: SSH con puerto alternativo
echo "Intento 2: Verificar puertos alternativos"
for port in 2222 22222; do
    echo "  Probando puerto $port..."
    timeout 10 ssh -p $port -o ConnectTimeout=5 root@$SERVER 'echo "Conectado en puerto '$port'"' 2>/dev/null && exit 0
done

# Intento 3: SSH desde IP diferente (si tienes VPN local)
echo "Intento 3: ¿Tienes VPN local para probar desde Colombia?"

echo "=== No se pudo conectar por SSH ==="
echo "Esto es normal si la VPN del servidor está bloqueando conexiones externas"
echo "El bot puede estar funcionando correctamente de todos modos"
echo ""
echo "Para verificar el estado:"
echo "1. Revisa los mensajes de Telegram que estás recibiendo"
echo "2. Busca el bot en tu panel de DigitalOcean"
echo "3. Usa la consola web de DigitalOcean si está disponible"