# Despliegue del Dragon Bot (DigitalOcean)

**Objetivo:** que el bot funcione **24 horas** en el servidor, **sin tener la página del casino abierta en tu Mac**. En el servidor corre en modo **headless** (sin ventana de navegador).

**Servidor en uso:** un solo droplet. El anterior se eliminó porque el casino bloqueaba esa IP/región; este es el nuevo para evitar el bloqueo.

## Servidor (Droplet)

| Servidor | IP | Uso |
|----------|-----|-----|
| **Producción** | `134.209.37.219` | Dragon Bot ML 24/7 (headless) |

Conectar por SSH:
```bash
ssh root@134.209.37.219
```

---

## Desplegar desde tu Mac (recomendado)

Desde la raíz del proyecto en tu Mac:

```bash
cd /Users/miguelantonio/Desktop/EVOLUTION-SCRAPER
bash deploy/deploy_from_mac.sh
```

Eso sube el código al servidor (sin `venv`, sin `.env`, sin `browser_data`). Luego:

1. **Solo la primera vez:** crear `.env` en el servidor y ejecutar el setup.
2. **Sesión del casino:** hacer login **en tu Mac** (ver abajo), guardar la sesión y subir `storage_state.json` al servidor.

---

## Cómo hacer "login manual" cuando el bot está en producción

El bot en el servidor no tiene pantalla: no puedes abrir un navegador allí y escribir usuario/contraseña. La solución es **hacer el login una vez en tu Mac**, guardar la sesión (cookies) y **subir ese archivo al servidor**. El bot en producción usará esa sesión y entrará ya logueado.

### Pasos (en tu Mac)

1. **Conéctate con VPN a Colombia** (o desde la red donde el casino te deja entrar) y abre el proyecto:
   ```bash
   cd /Users/miguelantonio/Desktop/EVOLUTION-SCRAPER
   ```

2. **Activa el venv y ejecuta el script que abre el navegador:**
   ```bash
   source venv/bin/activate
   python save_storage_state.py
   ```
   Se abrirá una ventana de Chrome con la página del casino.

3. **Inicia sesión manualmente** en esa ventana (usuario y contraseña del casino). Entra hasta la mesa del juego (XXXtreme Lightning Baccarat).

4. **Cuando ya estés dentro de la mesa**, en otra terminal:
   ```bash
   touch storage_state.ready
   ```
   El script detectará el archivo y guardará la sesión en `storage_state.json`. La ventana se cerrará.

5. **Sube la sesión al servidor:**
   ```bash
   scp storage_state.json root@134.209.37.219:/root/EVOLUTION-SCRAPER/
   ```

6. **Reinicia el bot en el servidor** para que cargue la nueva sesión:
   ```bash
   ssh root@134.209.37.219 'systemctl restart dragonbot'
   ```

A partir de ahí el bot en producción usará esa sesión. Cuando el casino cierre la sesión (p. ej. al cabo de días), repite los pasos 1–6 para generar un nuevo `storage_state.json` y subirlo.

### Primera vez en el servidor

```bash
# 1. Subir proyecto
bash deploy/deploy_from_mac.sh

# 2. Crear .env en el servidor (credenciales Telegram + casino)
scp .env root@134.209.37.219:/root/EVOLUTION-SCRAPER/

# 3. Opcional: copiar sesión del casino (si ya iniciaste sesión en tu Mac)
scp storage_state.json root@134.209.37.219:/root/EVOLUTION-SCRAPER/

# 4. Conectar al servidor y ejecutar setup (venv, PostgreSQL, Playwright)
ssh root@134.209.37.219 'cd /root/EVOLUTION-SCRAPER && PROJECT_DIR=/root/EVOLUTION-SCRAPER bash deploy/do_setup.sh'

# 5. Instalar servicio e iniciar bot 24/7
ssh root@134.209.37.219 'sudo cp /root/EVOLUTION-SCRAPER/deploy/dragonbot.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable dragonbot && sudo systemctl start dragonbot'
```

### Actualizar código y reiniciar

```bash
bash deploy/deploy_from_mac.sh
# Responde "s" cuando pregunte si instalar/reiniciar servicio
```

O manualmente:
```bash
rsync -avz --exclude venv --exclude .env --exclude browser_data ... (ver deploy_from_mac.sh)
ssh root@134.209.37.219 'sudo systemctl restart dragonbot'
```

---

## VPN Colombia (el casino solo permite acceso desde Colombia)

**DigitalOcean no tiene “VPN” como opción.** Tú instalas un **cliente VPN** en el droplet y te conectas a un proveedor externo (NordVPN, ProtonVPN, etc.) con servidores en Colombia. Guía paso a paso:

- **Ver:** [deploy/VPN_COLOMBIA.md](VPN_COLOMBIA.md) — cómo instalar VPN en el servidor (**FastestVPN**, NordVPN, ProtonVPN, OpenVPN).

### Opción A: VPN en todo el servidor (recomendado)

1. Contratar un VPN con servidores en Colombia (NordVPN, ProtonVPN, etc.).
2. En el servidor: instalar el cliente y conectarte a **Colombia** (comandos en `VPN_COLOMBIA.md`).
3. Arrancar el bot: `systemctl start dragonbot`. No hace falta `PROXY_URL`.

### Opción B: Solo el bot por proxy (PROXY_URL)

Si tienes un **proxy HTTP o SOCKS5** con IP en Colombia:

1. En el servidor, en `/root/EVOLUTION-SCRAPER/.env` añade:
   ```bash
   PROXY_URL=http://usuario:password@proxy-colombia:8080
   # o SOCKS5:
   PROXY_URL=socks5://usuario:password@proxy-colombia:1080
   ```
2. Reinicia el bot: `systemctl restart dragonbot`.

El navegador del bot usará ese proxy; el resto del servidor no.

---

## Qué hace el servidor

- **HEADLESS=1** → Chromium corre sin ventana (modo headless).
- **systemd** → Si el bot se cae, se reinicia solo (Restart=always).
- No necesitas tener el casino abierto en tu Mac; todo corre en el droplet.

## Ver logs en el servidor

```bash
ssh root@134.209.37.219
journalctl -u dragonbot -f
```

## Archivos en esta carpeta

- `deploy_from_mac.sh` – Sube el proyecto al servidor desde tu Mac.
- `do_setup.sh` – Instalación de dependencias y preparación de BD en el servidor.
- `dragonbot.service` – Unidad systemd para ejecutar el bot 24/7.
