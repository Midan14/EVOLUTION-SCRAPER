# 🚀 CREAR SERVIDOR NUEVO - DESDE CERO

Esta guía te llevará paso a paso para crear un servidor completamente nuevo en DigitalOcean y desplegar el bot.

---

## PASO 1: Eliminar el Droplet Anterior (Opcional)

Si quieres eliminar el droplet viejo (165.232.142.48):

1. Ve a: https://cloud.digitalocean.com/
2. Encuentra el droplet con IP **165.232.142.48**
3. Haz clic en **"More"** → **"Destroy"**
4. Confirma la eliminación
5. ⚠️ **Importante:** Si tienes backups o snapshots, guárdalos antes

---

## PASO 2: Crear Nuevo Droplet

### 2.1. Crear el Droplet

1. En DigitalOcean: https://cloud.digitalocean.com/
2. Haz clic en **"Create"** → **"Droplets"**
3. Configura así:

**Imagen:**
- **Ubuntu 22.04 LTS** (o 24.04 LTS)

**Plan:**
- **Basic** (Shared CPU)
- **$12/mes** (2 GB RAM / 1 CPU) - mínimo recomendado
- O **$18/mes** (2 GB RAM / 2 CPU) - mejor rendimiento

**Datacenter:**
- **Elige el más cercano a Colombia:**
  - Miami, Florida (mia)
  - New York (nyc)
  - Toronto, Canada (tor)
- ⚠️ NO importa la región, usarás VPN a Colombia después

**Autenticación:**
- **SSH Key** (recomendado - más seguro)
- O **Password** (más simple pero menos seguro)

**Opciones adicionales:**
- ✅ Marca: **IPv6**
- ❌ NO marques: Monitoring, Backups (opcional, cuestan extra)

**Hostname:**
- Ponle un nombre descriptivo: `dragonbot-prod` o `evolution-bot`

4. Haz clic en **"Create Droplet"**
5. Espera 1-2 minutos a que se cree
6. **Anota la nueva IP** (ejemplo: 142.93.XXX.XXX)

### 2.2. Probar Conexión SSH

```bash
# Reemplaza NEW_IP con la IP que te dio DigitalOcean
ssh root@NEW_IP
```

Si es la primera vez, dirá:
```
The authenticity of host... Are you sure you want to continue? (yes/no)
```
Escribe **`yes`** y presiona Enter.

Si conecta, verás algo como:
```
root@dragonbot-prod:~#
```

✅ **¡Conexión exitosa!** - Puedes salir escribiendo `exit`

---

## PASO 3: Actualizar IP en tu Proyecto

En tu Mac, actualiza todos los archivos que tengan la IP vieja:

```bash
cd /Users/miguelantonio/Desktop/EVOLUTION-SCRAPER

# Buscar archivos con la IP vieja
grep -r "165.232.142.48" deploy/ README.md digitalocean_logs_guide.md

# Reemplazar manualmente en cada archivo o usar sed:
# (REEMPLAZA NEW_IP con tu nueva IP)
find . -type f -name "*.md" -o -name "*.sh" | xargs sed -i '' 's/165.232.142.48/NEW_IP/g'
```

O hazlo manualmente en estos archivos:
- `deploy/README.md`
- `deploy/diagnose_server.sh`
- `deploy/deploy_from_mac.sh`
- `digitalocean_logs_guide.md`

---

## PASO 4: Configurar el Servidor (Primera vez)

### 4.1. Subir el Proyecto

```bash
cd /Users/miguelantonio/Desktop/EVOLUTION-SCRAPER

# Ejecutar deploy (creará la estructura en el servidor)
bash deploy/deploy_from_mac.sh
```

Te preguntará la IP del servidor - ingresa la **nueva IP**.

### 4.2. Crear archivo .env en el Servidor

Primero, verifica que tengas tu `.env` local:

```bash
cat .env
```

Debería tener algo como:
```
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id
DB_URL=postgresql://root:DragonBotRoot2026!@localhost/dragon_bot
TARGET_URL=https://dragonslots-1.com/es/live-casino/game/evolution/xxxtremelightningbaccarat
HEADLESS=1
```

Copia el `.env` al servidor:

```bash
scp .env root@NEW_IP:/root/EVOLUTION-SCRAPER/
```

### 4.3. Ejecutar Setup Inicial

Conecta al servidor:

```bash
ssh root@NEW_IP
```

Una vez dentro, ejecuta:

```bash
cd /root/EVOLUTION-SCRAPER
PROJECT_DIR=/root/EVOLUTION-SCRAPER bash deploy/do_setup.sh
```

Esto instalará:
- Python 3 y dependencias
- PostgreSQL
- Playwright + Chromium
- Creará la base de datos

El proceso tarda 5-10 minutos. Verás mucho output.

---

## PASO 5: Configurar VPN (Colombia)

### 5.1. Instalar OpenVPN

```bash
apt update && apt install -y openvpn unzip wget
```

### 5.2. Subir Configs de FastestVPN

**Opción A: Si tienes el archivo en tu Mac**

```bash
# Desde tu Mac
scp ~/Downloads/fastestvpn_ovpn.zip root@NEW_IP:/root/
```

**Opción B: Descargar en el servidor**

```bash
# Desde el servidor (si la URL pública funciona)
cd /root
wget "https://support.fastestvpn.com/download/fastestvpn_ovpn/" -O fastestvpn_ovpn.zip
```

### 5.3. Configurar VPN de Colombia

En el servidor:

```bash
cd /root
unzip -o fastestvpn_ovpn.zip

# Buscar config de Colombia
find /root -name "*.ovpn" | xargs grep -l -i colombia 2>/dev/null

# Copiar el config (ajusta la ruta según lo que encuentres)
cp /root/tcp/colombia-tcp.ovpn /root/fastestvpn-colombia.ovpn

# Crear archivo de autenticación
echo "TU_USUARIO_FASTESTVPN" > /root/fastestvpn.auth
echo "TU_CONTRASEÑA_FASTESTVPN" >> /root/fastestvpn.auth
chmod 600 /root/fastestvpn.auth

# Agregar línea de auth al config
echo "auth-user-pass /root/fastestvpn.auth" >> /root/fastestvpn-colombia.ovpn
```

### 5.4. Probar VPN manualmente

```bash
# Ver IP antes de VPN
curl ifconfig.me

# Conectar VPN (en primer plano para ver errores)
openvpn /root/fastestvpn-colombia.ovpn
```

Si funciona, verás: **"Initialization Sequence Completed"**

Presiona **Ctrl+C** para detener.

### 5.5. Crear Servicio VPN (para que inicie automáticamente)

```bash
cat > /etc/systemd/system/fastestvpn.service << 'EOF'
[Unit]
Description=FastestVPN Colombia
After=network.target
Before=dragonbot.service

[Service]
Type=simple
ExecStart=/usr/sbin/openvpn /root/fastestvpn-colombia.ovpn
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Habilitar e iniciar
systemctl daemon-reload
systemctl enable fastestvpn
systemctl start fastestvpn

# Verificar
sleep 5
systemctl status fastestvpn

# Verificar IP (debe ser de Colombia ahora)
curl ifconfig.me
```

---

## PASO 6: Hacer Login en el Casino (En tu Mac)

⚠️ **IMPORTANTE:** El bot necesita una sesión activa del casino. Debes hacer el login en tu Mac y subir la sesión.

### 6.1. Conectarte a VPN Colombia (en tu Mac)

Usa tu VPN personal (FortiClient, ProtonVPN, etc.) y conéctate a un servidor de Colombia.

### 6.2. Hacer Login

En tu Mac:

```bash
cd /Users/miguelantonio/Desktop/EVOLUTION-SCRAPER
source venv/bin/activate
python save_storage_state.py
```

Se abrirá un navegador. **Haz login manualmente** en el casino y entra a la mesa XXXtreme Lightning Baccarat.

Cuando estés dentro del juego, en otra terminal:

```bash
touch storage_state.ready
```

El navegador se cerrará y se guardará `storage_state.json`.

### 6.3. Subir Sesión al Servidor

```bash
scp storage_state.json root@NEW_IP:/root/EVOLUTION-SCRAPER/
```

---

## PASO 7: Instalar y Activar el Bot como Servicio

En el servidor:

```bash
# Copiar el archivo de servicio
cp /root/EVOLUTION-SCRAPER/deploy/dragonbot.service /etc/systemd/system/

# Recargar systemd
systemctl daemon-reload

# Habilitar el bot (se iniciará automáticamente al reiniciar servidor)
systemctl enable dragonbot

# Iniciar el bot
systemctl start dragonbot

# Verificar estado
systemctl status dragonbot
```

Si todo está bien, verás: **"active (running)"**

---

## PASO 8: Verificar que Todo Funciona

### 8.1. Ver Logs en Tiempo Real

```bash
journalctl -u dragonbot -f
```

Presiona **Ctrl+C** para salir.

### 8.2. Ver Estado de Servicios

```bash
systemctl status dragonbot
systemctl status postgresql
systemctl status fastestvpn
```

### 8.3. Verificar en Telegram

Revisa tu chat de Telegram - el bot debe empezar a enviarte mensajes con análisis de las manos.

---

## PASO 9: Comandos Útiles para Administración

```bash
# Reiniciar el bot
systemctl restart dragonbot

# Ver logs recientes
journalctl -u dragonbot -n 50

# Ver logs con timestamps
journalctl -u dragonbot -n 30 --since "1 hour ago"

# Ver IP actual (verificar VPN)
curl ifconfig.me

# Ver uso de recursos
htop

# Ver espacio en disco
df -h
```

---

## 🎯 CHECKLIST FINAL

- [ ] Droplet nuevo creado y accesible por SSH
- [ ] IP actualizada en todos los archivos del proyecto
- [ ] Código subido al servidor
- [ ] Archivo `.env` copiado al servidor
- [ ] Setup ejecutado (PostgreSQL, Python, Playwright)
- [ ] VPN configurada y funcionando (IP de Colombia)
- [ ] `storage_state.json` subido al servidor
- [ ] Servicio `dragonbot` instalado y corriendo
- [ ] Bot enviando mensajes a Telegram

---

## 🆘 TROUBLESHOOTING

### El bot no inicia

```bash
# Ver error específico
journalctl -u dragonbot -n 50

# Verificar que PostgreSQL esté corriendo
systemctl status postgresql

# Verificar que existan los archivos
ls -la /root/EVOLUTION-SCRAPER/.env
ls -la /root/EVOLUTION-SCRAPER/storage_state.json
```

### VPN no conecta

```bash
# Ver logs de VPN
journalctl -u fastestvpn -n 50

# Probar manualmente
openvpn /root/fastestvpn-colombia.ovpn
```

### Casino rechaza la sesión

- La sesión en `storage_state.json` expiró
- Solución: Repite el PASO 6 (hacer login de nuevo en tu Mac y subir nueva sesión)

---

## 📊 PRÓXIMOS PASOS

Una vez que el bot esté funcionando:

1. **Deja el servidor corriendo** - el bot funciona 24/7
2. **Revisa Telegram** - recibirás análisis en tiempo real
3. **Actualizar código:** usa `bash deploy/deploy_from_mac.sh`
4. **Renovar sesión:** cuando el casino cierre la sesión (cada varios días)

---

## 💡 TIPS

- **No necesitas SSH todo el tiempo** - usa la consola web de DigitalOcean si SSH falla
- **El bot es autónomo** - si envía mensajes a Telegram, está funcionando bien
- **Backups:** Crea snapshots del droplet ocasionalmente
- **Monitoreo:** Revisa las gráficas de CPU/RAM en el panel de DigitalOcean
