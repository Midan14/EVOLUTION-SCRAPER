#!/usr/bin/env bash
# Script para reparar problemas comunes del servidor
# Uso: bash deploy/fix_server.sh [restart|regenerate-session|install-deps|full-reset]

SERVER="165.232.142.48"
USER="root"
ACTION="${1:-restart}"

echo "🔧 Reparando servidor de producción..."
echo "   Acción: $ACTION"
echo ""

case "$ACTION" in
    restart)
        echo "♻️  Reiniciando servicio DragonBot..."
        ssh $USER@$SERVER 'systemctl restart dragonbot'
        sleep 5
        ssh $USER@$SERVER 'systemctl status dragonbot --no-pager | head -15'
        echo ""
        echo "✅ Servicio reiniciado. Verifica los logs:"
        echo "   ssh root@$SERVER 'journalctl -u dragonbot -f'"
        ;;
    
    restart-all)
        echo "♻️  Reiniciando todos los servicios..."
        ssh $USER@$SERVER 'systemctl restart postgresql'
        sleep 2
        ssh $USER@$SERVER 'systemctl restart fastestvpn 2>/dev/null || true'
        sleep 2
        ssh $USER@$SERVER 'systemctl restart dragonbot'
        sleep 5
        echo "✅ Todos los servicios reiniciados"
        ;;
    
    install-deps)
        echo "📦 Reinstalando dependencias..."
        ssh $USER@$SERVER 'cd /root/EVOLUTION-SCRAPER && source venv/bin/activate && pip install --upgrade -r requirements.txt && playwright install chromium --with-deps'
        echo "✅ Dependencias reinstaladas"
        ;;
    
    regenerate-session)
        echo "🔐 Para regenerar la sesión del casino:"
        echo ""
        echo "1. En tu Mac, con VPN a Colombia activa:"
        echo "   cd /Users/miguelantonio/Desktop/EVOLUTION-SCRAPER"
        echo "   source venv/bin/activate"
        echo "   python save_storage_state.py"
        echo ""
        echo "2. Cuando estés logueado en la mesa, en otra terminal:"
        echo "   touch storage_state.ready"
        echo ""
        echo "3. Sube la sesión al servidor:"
        echo "   scp storage_state.json root@$SERVER:/root/EVOLUTION-SCRAPER/"
        echo ""
        echo "4. Reinicia el bot:"
        echo "   ssh root@$SERVER 'systemctl restart dragonbot'"
        ;;
    
    full-reset)
        echo "🔄 Reset completo del bot (esto puede tomar varios minutos)..."
        echo ""
        echo "1️⃣  Deteniendo servicio..."
        ssh $USER@$SERVER 'systemctl stop dragonbot'
        
        echo "2️⃣  Limpiando browser_data..."
        ssh $USER@$SERVER 'rm -rf /root/EVOLUTION-SCRAPER/browser_data/*'
        
        echo "3️⃣  Reinstalando dependencias..."
        ssh $USER@$SERVER 'cd /root/EVOLUTION-SCRAPER && source venv/bin/activate && pip install --upgrade -r requirements.txt && playwright install chromium --with-deps'
        
        echo "4️⃣  Reiniciando PostgreSQL..."
        ssh $USER@$SERVER 'systemctl restart postgresql'
        sleep 3
        
        echo "5️⃣  Verificando VPN..."
        ssh $USER@$SERVER 'systemctl restart fastestvpn 2>/dev/null || echo "VPN no configurado"'
        sleep 3
        
        echo "6️⃣  Iniciando servicio..."
        ssh $USER@$SERVER 'systemctl start dragonbot'
        sleep 5
        
        echo ""
        echo "✅ Reset completo finalizado"
        ssh $USER@$SERVER 'systemctl status dragonbot --no-pager | head -15'
        ;;
    
    logs)
        echo "📋 Mostrando logs en tiempo real..."
        echo "   (Presiona Ctrl+C para salir)"
        echo ""
        ssh $USER@$SERVER 'journalctl -u dragonbot -f'
        ;;
    
    *)
        echo "❌ Acción desconocida: $ACTION"
        echo ""
        echo "Uso: bash deploy/fix_server.sh [ACCIÓN]"
        echo ""
        echo "Acciones disponibles:"
        echo "  restart           - Reinicia solo el bot (rápido)"
        echo "  restart-all       - Reinicia bot, PostgreSQL y VPN"
        echo "  install-deps      - Reinstala dependencias Python y Playwright"
        echo "  regenerate-session - Instrucciones para generar nueva sesión del casino"
        echo "  full-reset        - Reset completo (detener, limpiar, reinstalar todo)"
        echo "  logs              - Ver logs en tiempo real"
        echo ""
        echo "Ejemplos:"
        echo "  bash deploy/fix_server.sh restart"
        echo "  bash deploy/fix_server.sh full-reset"
        exit 1
        ;;
esac
