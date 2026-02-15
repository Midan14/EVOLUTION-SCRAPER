# Cómo instalar VPN (Colombia) en el servidor DigitalOcean

**DigitalOcean no tiene “VPN” como servicio.** Lo que haces es: en tu droplet (el servidor) instalas un **cliente VPN** y te conectas a un **proveedor de VPN externo** que tenga servidores en Colombia. Todo el tráfico del servidor (incluido el bot) saldrá por Colombia.

---

## Resumen rápido

1. Contratas o usas una VPN con servidores en **Colombia** (FastestVPN, NordVPN, ProtonVPN, etc.).
2. Te conectas por SSH al droplet: `ssh root@165.232.142.48`
3. Instalas el cliente VPN en el droplet y te conectas a un servidor en Colombia.
4. Dejas la VPN activa y reinicias el bot: `systemctl restart dragonbot`.

---

## FastestVPN (Colombia con OpenVPN)

FastestVPN tiene servidor en **Colombia** (Bogotá). En Linux se usa OpenVPN con archivos `.ovpn`.

### 1. Conectarte al servidor

```bash
ssh root@165.232.142.48
```

### 2. Instalar OpenVPN y dependencias

```bash
apt update && apt install -y openvpn unzip wget
```

### 3. Configs de FastestVPN (zip)

**Si ya tienes el zip en el servidor** (por ejemplo en `/root/fastestvpn_ovpn.zip`):
```bash
cd /root
unzip -o fastestvpn_ovpn.zip
```

**Si aún no lo tienes:**

- **Opción A – Desde el servidor (si la URL pública funciona):**
```bash
cd /root
wget "https://support.fastestvpn.com/download/fastestvpn_ovpn/" -O fastestvpn_ovpn.zip
unzip -o fastestvpn_ovpn.zip
```

- **Opción B – Desde tu Mac:** entra en [FastestVPN Support – OpenVPN Linux](https://support.fastestvpn.com/tutorials/linux/openvpn-cli/), inicia sesión y descarga el zip. Luego súbelo al servidor:
```bash
scp /ruta/descargas/fastestvpn_ovpn.zip root@165.232.142.48:/root/
ssh root@165.232.142.48 'cd /root && unzip -o fastestvpn_ovpn.zip'
```

### 4. Buscar el archivo de Colombia

Los configs suelen estar en carpetas `tcp` y `udp`. El de Colombia puede llamarse `colombia.ovpn`, `co.ovpn` o similar:

```bash
find /root -name "*.ovpn" | xargs grep -l -i colombia 2>/dev/null
# o listar todos y elegir:
ls -la /root/*.ovpn 2>/dev/null; ls -la /root/*/*.ovpn 2>/dev/null
```

Copia el `.ovpn` de Colombia a un nombre fijo, por ejemplo:

```bash
cp /root/tcp/colombia-tcp.ovpn /root/fastestvpn-colombia.ovpn
# (ajusta la ruta y nombre según lo que tengas)
```

### 5. Crear archivo con tu usuario y contraseña (para que no pida teclearlos)

```bash
echo "TU_USUARIO_FASTESTVPN" > /root/fastestvpn.auth
echo "TU_CONTRASEÑA_FASTESTVPN" >> /root/fastestvpn.auth
chmod 600 /root/fastestvpn.auth
```

Edita el `.ovpn` para usar ese archivo. Añade una línea al final del config:

```bash
echo "auth-user-pass /root/fastestvpn.auth" >> /root/fastestvpn-colombia.ovpn
```

### 6. Conectar a la VPN y comprobar que todo el tráfico sale por la VPN

**Paso A – Comprobar que tienes los archivos en el servidor:**
```bash
ls -la /root/fastestvpn-colombia.ovpn /root/fastestvpn.auth
# Deben existir ambos. Si no, vuelve a los pasos 4 y 5.
```

**Paso B – Conectar la VPN (prueba manual, en primer plano):**
```bash
# Ver la IP ANTES de conectar (anótala; suele ser 165.232.142.48)
curl -s ifconfig.me
echo ""

# Conectar OpenVPN (queda en primer plano; si conecta bien verás "Initialization Sequence Completed")
openvpn --config /root/fastestvpn-colombia.ovpn
```
En otra terminal SSH (segunda sesión):
```bash
ssh root@165.232.142.48
curl -s ifconfig.me
```
Si ahora ves **otra IP** (no la de DigitalOcean), la VPN está enviando el tráfico por Colombia. Pulsa `Ctrl+C` en la terminal donde corre OpenVPN para cerrarla; luego usa el **servicio** (paso 7) para dejarla siempre activa.

**Paso B alternativo – Usar el servicio directo (sin prueba manual):**
```bash
systemctl start fastestvpn
sleep 10
curl -s ifconfig.me
```
Si ves una IP distinta a la de DigitalOcean, la VPN está activa y el tráfico sale por ella.

### 7. Servicio para que la VPN arranque al reiniciar el servidor

```bash
cat > /etc/systemd/system/fastestvpn.service << 'EOF'
[Unit]
Description=FastestVPN Colombia
After=network.target

[Service]
Type=simple
ExecStart=/usr/sbin/openvpn --config /root/fastestvpn-colombia.ovpn
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable fastestvpn
systemctl start fastestvpn
```

(El `.ovpn` ya incluye `auth-user-pass /root/fastestvpn.auth` si lo añadiste en el paso 5.)

**Si `curl ifconfig.me` sigue mostrando la IP de DigitalOcean** después de conectar la VPN:
- El config `.ovpn` debe enviar todo el tráfico por la VPN. Revisa si tiene `redirect-gateway` o `redirect-gateway def1`. Si no, añade en `/root/fastestvpn-colombia.ovpn` una línea: `redirect-gateway def1` y reinicia: `systemctl restart fastestvpn`.
- Comprueba el estado: `systemctl status fastestvpn` y `journalctl -u fastestvpn -n 30`.

### 8. Reiniciar el bot

```bash
systemctl restart dragonbot
journalctl -u dragonbot -f
```

Cuando veas `✅ WebSocket del juego conectado`, las señales llegarán a Telegram.

---

## Si el bot pide "login manual" en producción

No puedes teclear en el servidor. La solución es **hacer el login en tu Mac**, guardar la sesión (cookies) y subirla al servidor. Ver la sección **"Cómo hacer login manual cuando el bot está en producción"** en `deploy/README.md`: ejecutar `save_storage_state.py` en tu Mac, iniciar sesión en el navegador que se abre, crear `storage_state.ready`, luego subir `storage_state.json` al servidor con `scp` y reiniciar el bot.

---

## Opción 1: NordVPN (de pago, muy sencillo en Linux)

NordVPN tiene servidores en Colombia y app para Linux.

1. **Cuenta:** Regístrate en [nordvpn.com](https://nordvpn.com) y anota usuario/contraseña.

2. **En el servidor (SSH):**
   ```bash
   ssh root@165.232.142.48
   ```

3. **Instalar NordVPN:**
   ```bash
   sh <(curl -sSf https://downloads.nordcdn.com/apps/linux/install.sh)
   ```

4. **Iniciar sesión y conectar a Colombia:**
   ```bash
   nordvpn login
   # Te pedirá un enlace; ábrelo en el navegador, inicia sesión y autoriza el dispositivo.
   
   nordvpn connect Colombia
   ```

5. **Comprobar que sales por Colombia:**
   ```bash
   nordvpn status
   curl -s ifconfig.me
   # Debería mostrarte una IP que no sea la de DigitalOcean.
   ```

6. **Reiniciar el bot:**
   ```bash
   systemctl restart dragonbot
   journalctl -u dragonbot -f
   ```

7. **Para que la VPN se conecte al reiniciar el servidor (opcional):**
   ```bash
   nordvpn set autoconnect on
   ```

---

## Opción 2: ProtonVPN (tiene plan gratuito)

ProtonVPN tiene servidores en Colombia y CLI para Linux.

1. **Cuenta:** [protonvpn.com](https://protonvpn.com) → plan gratuito o de pago.

2. **En el servidor:**
   ```bash
   ssh root@165.232.142.48
   apt update && apt install -y wireguard
   ```

3. **Instalar ProtonVPN CLI** (sigue la guía oficial para Linux):  
   [https://protonvpn.com/support/linux-vpn-setup/](https://protonvpn.com/support/linux-vpn-setup/)

   Ejemplo con Debian/Ubuntu:
   ```bash
   apt install -y openvpn
   # Luego descarga los .ovpn de Colombia desde tu cuenta ProtonVPN
   # y conéctate con: openvpn --config tu-archivo-colombia.ovpn
   ```

   O usa la CLI oficial de ProtonVPN si está disponible para tu distro.

4. Conectarte a un servidor **Colombia**, comprobar IP con `curl -s ifconfig.me` y luego:
   ```bash
   systemctl restart dragonbot
   ```

---

## Opción 3: OpenVPN con cualquier proveedor

Si ya tienes una VPN que te da archivos **.ovpn** (OpenVPN) para Colombia:

1. **En tu Mac:** descarga el `.ovpn` del servidor Colombia de tu proveedor.

2. **Sube el archivo al servidor:**
   ```bash
   scp ruta/al/colombia.ovpn root@165.232.142.48:/root/
   ```

3. **En el servidor:**
   ```bash
   ssh root@165.232.142.48
   apt update && apt install -y openvpn
   openvpn --config /root/colombia.ovpn --daemon
   ```

4. Comprueba la IP: `curl -s ifconfig.me`, luego:
   ```bash
   systemctl restart dragonbot
   ```

---

## Resumen

| Qué hace DigitalOcean | Qué haces tú |
|------------------------|--------------|
| No ofrece VPN integrada | Instalas un **cliente VPN** en el droplet |
| El droplet es un VPS normal | Te conectas a un **proveedor externo** (NordVPN, ProtonVPN, etc.) con servidor en **Colombia** |
| — | Todo el tráfico del servidor (incluido el bot) sale por Colombia → el casino permite acceso |

Recomendación: **NordVPN** (Opción 1) es la más directa: un script de instalación, `nordvpn connect Colombia` y listo. Si prefieres algo gratuito, usa **ProtonVPN** (Opción 2) o cualquier otro que te dé OpenVPN para Colombia (Opción 3).
