# GUÍA: Acceder a logs via Panel DigitalOcean

## Opción 1: Consola Web (Más fácil)
1. Ir a: https://cloud.digitalocean.com/
2. Login con tu cuenta
3. Buscar el droplet con IP 165.227.69.58
4. Hacer clic en "Console" o "Access Console"
5. Una vez dentro del servidor:

# Ver logs en tiempo real del bot
journalctl -u dragonbot -f

# Ver últimos 50 logs
journalctl -u dragonbot -n 50

# Ver logs con timestamps
journalctl -u dragonbot -n 30 --since "1 hour ago"

# Ver estado del servicio
systemctl status dragonbot

# Ver estado de la VPN
systemctl status fastestvpn

## Opción 2: Monitoreo via Panel
- Gráficas de CPU/Memoria
- Bandwidth usage  
- Sistema alerts
- Resource usage en tiempo real

## Opción 3: Logs del Sistema
- System logs en el panel
- Kernel messages
- Service logs

## Si el servidor parece estar mal:
# Reiniciar el bot
systemctl restart dragonbot

# Revisar si la VPN está funcionando
curl ifconfig.me

# Ver uso de recursos
htop

IMPORTANTE: El bot envía toda la información importante via Telegram,
así que los logs principalmente servirán para debug técnico.