# 🚀 RESUMEN EJECUTIVO - NUEVO SERVIDOR

## TL;DR (Too Long; Didn't Read)

1. **Crear droplet en DigitalOcean** → Ubuntu 22.04, 2GB RAM, anota la nueva IP
2. **Ejecutar:** `bash deploy/quick_start_new_server.sh` → automático
3. **Configurar VPN** → ver `deploy/VPN_COLOMBIA.md`
4. **Login casino** → `python save_storage_state.py` → subir archivo
5. **Activar bot** → `systemctl start dragonbot`

---

## SCRIPTS DISPONIBLES

### 🆕 Para servidor NUEVO:

```bash
# Opción 1: Setup automático (recomendado)
bash deploy/quick_start_new_server.sh

# Opción 2: Solo actualizar IP en archivos
bash deploy/update_server_ip.sh
```

### 🔧 Para servidor EXISTENTE:

```bash
# Diagnóstico completo
bash deploy/diagnose_server.sh

# Solo verificar estado
bash deploy/check_server_status.sh

# Actualizar código
bash deploy/deploy_from_mac.sh
```

---

## PASO A PASO SIMPLIFICADO

### 1. En DigitalOcean Panel

1. Ir a: https://cloud.digitalocean.com/
2. Create → Droplets
3. Ubuntu 22.04 LTS
4. Plan: $12/mes (2GB RAM)
5. Datacenter: Miami o New York
6. SSH Key o Password
7. Create Droplet
8. **Anotar la nueva IP**

### 2. En tu Mac - Setup Automático

```bash
cd /Users/miguelantonio/Desktop/EVOLUTION-SCRAPER
bash deploy/quick_start_new_server.sh
```

Sigue las instrucciones del script.

### 3. Configurar VPN en el Servidor

```bash
ssh root@NUEVA_IP

# Instalar OpenVPN
apt update && apt install -y openvpn unzip

# Subir configs de FastestVPN (desde tu Mac)
# exit del servidor primero, luego:
scp ~/Downloads/fastestvpn_ovpn.zip root@NUEVA_IP:/root/

# Volver al servidor
ssh root@NUEVA_IP
cd /root
unzip fastestvpn_ovpn.zip

# Buscar config de Colombia
find /root -name "*.ovpn" | xargs grep -l -i colombia

# Copiar y configurar (ajusta la ruta)
cp /root/tcp/colombia-tcp.ovpn /root/fastestvpn-colombia.ovpn

# Crear archivo de autenticación
echo "TU_USUARIO" > /root/fastestvpn.auth
echo "TU_PASSWORD" >> /root/fastestvpn.auth
chmod 600 /root/fastestvpn.auth

# Agregar auth al config
echo "auth-user-pass /root/fastestvpn.auth" >> /root/fastestvpn-colombia.ovpn

# Crear servicio
cat > /etc/systemd/system/fastestvpn.service << 'EOF'
[Unit]
Description=FastestVPN Colombia
After=network.target

[Service]
Type=simple
ExecStart=/usr/sbin/openvpn /root/fastestvpn-colombia.ovpn
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Activar VPN
systemctl daemon-reload
systemctl enable fastestvpn
systemctl start fastestvpn

# Verificar IP (debe ser de Colombia)
sleep 10
curl ifconfig.me
```

### 4. Hacer Login en Casino (en tu Mac)

```bash
# Conectarte a VPN Colombia en tu Mac primero
cd /Users/miguelantonio/Desktop/EVOLUTION-SCRAPER
source venv/bin/activate
python save_storage_state.py

# En otra terminal cuando estés en el juego:
touch storage_state.ready

# Subir sesión al servidor
scp storage_state.json root@NUEVA_IP:/root/EVOLUTION-SCRAPER/
```

### 5. Activar el Bot

```bash
ssh root@NUEVA_IP

# Instalar servicio
cp /root/EVOLUTION-SCRAPER/deploy/dragonbot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable dragonbot
systemctl start dragonbot

# Verificar
systemctl status dragonbot
journalctl -u dragonbot -f
```

### 6. Verificar en Telegram

Revisa tu chat - debes recibir mensajes del bot con análisis de manos.

---

## TIEMPOS ESTIMADOS

- Crear droplet: **2-3 minutos**
- Script automático: **10-15 minutos**
- Configurar VPN: **5 minutos**
- Login casino: **2-3 minutos**
- Activar bot: **1 minuto**

**Total: ~30 minutos**

---

## COMANDOS ÚTILES POST-SETUP

```bash
# Ver logs en tiempo real
ssh root@NUEVA_IP 'journalctl -u dragonbot -f'

# Reiniciar bot
ssh root@NUEVA_IP 'systemctl restart dragonbot'

# Ver estado de todo
ssh root@NUEVA_IP 'systemctl status dragonbot postgresql fastestvpn'

# Ver IP actual (verificar VPN)
ssh root@NUEVA_IP 'curl ifconfig.me'
```

---

## ARCHIVOS DE AYUDA

- **`deploy/CREAR_SERVIDOR_NUEVO.md`** - Guía completa y detallada
- **`deploy/VPN_COLOMBIA.md`** - Setup detallado de VPN
- **`deploy/README.md`** - Documentación general
- **`TROUBLESHOOTING_SERVIDOR.md`** - Solución de problemas

---

## MANTENIMIENTO

### Actualizar código:
```bash
bash deploy/deploy_from_mac.sh
```

### Renovar sesión del casino:
```bash
# En tu Mac (con VPN Colombia)
python save_storage_state.py
touch storage_state.ready
scp storage_state.json root@NUEVA_IP:/root/EVOLUTION-SCRAPER/
ssh root@NUEVA_IP 'systemctl restart dragonbot'
```

### Si el bot se cae:
```bash
ssh root@NUEVA_IP 'systemctl restart dragonbot'
```

---

## CHECKLIST PRE-DEPLOYMENT

- [ ] Tienes cuenta en DigitalOcean
- [ ] Tienes credenciales de FastestVPN (usuario/password)
- [ ] Tienes token de Telegram Bot
- [ ] Tienes chat ID de Telegram
- [ ] Tienes credenciales del casino
- [ ] Tienes VPN personal a Colombia (para hacer login en tu Mac)

---

## SOPORTE

Si algo falla:

1. **Ver logs:** `journalctl -u dragonbot -n 100`
2. **Verificar servicios:** `systemctl status dragonbot postgresql fastestvpn`
3. **Revisar archivos:** `ls -la /root/EVOLUTION-SCRAPER/.env storage_state.json`
4. **Consola web:** Panel de DigitalOcean → Console

El bot envía errores importantes a Telegram, así que revisa tu chat.
