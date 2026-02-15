# 🚨 GUÍA DE EMERGENCIA - SERVIDOR NO RESPONDE

## ⚠️ PROBLEMA DETECTADO

El servidor **165.227.69.58** no responde a:
- ❌ PING (servidor puede estar apagado o inaccesible)
- ❌ SSH Puerto 22 (no se puede conectar remotamente)

## 🔍 DIAGNÓSTICO

Esto significa que:
1. **El droplet puede estar apagado** en DigitalOcean
2. **La VPN está bloqueando todo** el tráfico entrante (incluido SSH)
3. **Hay un problema de red** en el servidor
4. **El servidor se crasheó** y necesita reinicio

---

## 🛠️ SOLUCIONES PASO A PASO

### PASO 1: Verificar si el droplet está encendido

1. Entra a: **https://cloud.digitalocean.com/**
2. Inicia sesión con tu cuenta
3. Busca el droplet con IP **165.227.69.58**
4. Verifica el estado:
   - ✅ Si dice **"Active"** o **"ON"** → pasa al PASO 2
   - ❌ Si dice **"Off"** o apagado → **ENCIÉNDELO** desde el panel

### PASO 2: Acceder via Consola Web (no requiere SSH)

1. En el panel de DigitalOcean, haz clic en tu droplet
2. Haz clic en **"Console"** o **"Access"** en el menú lateral
3. Se abrirá una terminal directa en tu navegador
4. Una vez dentro, ejecuta estos comandos:

```bash
# Ver si el bot está corriendo
systemctl status dragonbot

# Ver últimos 50 logs del bot
journalctl -u dragonbot -n 50

# Ver logs en tiempo real
journalctl -u dragonbot -f

# Si el bot está caído, reiniciarlo
systemctl restart dragonbot

# Verificar si VPN está activa
systemctl status fastestvpn

# Ver IP actual (debe ser de Colombia si VPN funciona)
curl ifconfig.me
```

### PASO 3: Si el bot no responde - Reiniciar servicios

Desde la consola web de DigitalOcean:

```bash
# Reiniciar PostgreSQL
systemctl restart postgresql

# Reiniciar VPN (puede estar causando problemas)
systemctl restart fastestvpn

# Esperar 10 segundos
sleep 10

# Reiniciar el bot
systemctl restart dragonbot

# Verificar que todo esté corriendo
systemctl status dragonbot
systemctl status postgresql
systemctl status fastestvpn
```

### PASO 4: Si nada funciona - Reboot completo

**Opción A: Desde la consola web**
```bash
reboot
```

**Opción B: Desde el panel de DigitalOcean**
1. En el droplet, haz clic en **"Power"**
2. Selecciona **"Reboot"** o **"Power Cycle"**
3. Espera 2-3 minutos
4. Vuelve a intentar acceder por SSH o consola web

### PASO 5: Verificar que el bot funciona

1. **Revisa tu Telegram**: ¿El bot te ha enviado mensajes recientemente?
   - ✅ Si hay mensajes → El bot está funcionando
   - ❌ Si no hay mensajes → El bot está caído

2. **Desde la consola web, revisa los logs:**
   ```bash
   journalctl -u dragonbot -n 100 --no-pager
   ```

3. **Busca errores comunes:**
   - `storage_state.json` expirado → Necesitas renovar sesión del casino
   - Error de PostgreSQL → La base de datos no está respondiendo
   - Error de Playwright → El navegador no se puede iniciar

---

## 🔧 PROBLEMAS COMUNES Y SOLUCIONES

### A. La VPN está bloqueando SSH

**Síntoma:** No puedes conectarte por SSH pero el droplet está encendido

**Solución temporal (desde consola web):**
```bash
# Detener VPN temporalmente
systemctl stop fastestvpn

# Esperar 30 segundos y probar SSH desde tu Mac
```

Luego desde tu Mac:
```bash
ssh root@165.227.69.58
```

Una vez dentro, reactiva la VPN:
```bash
systemctl start fastestvpn
```

### B. El bot dice "storage_state expirado"

**Síntoma:** Logs muestran error de autenticación con el casino

**Solución:**
1. **En tu Mac**, con VPN a Colombia activa:
   ```bash
   cd /Users/miguelantonio/Desktop/EVOLUTION-SCRAPER
   python save_storage_state.py
   ```

2. Inicia sesión manualmente en el navegador

3. Cuando estés dentro del juego:
   ```bash
   touch storage_state.ready
   ```

4. Sube el archivo al servidor (si hay SSH):
   ```bash
   scp storage_state.json root@165.227.69.58:/root/EVOLUTION-SCRAPER/
   ```

5. Si NO hay SSH, usa la consola web de DigitalOcean para copiar/pegar el contenido

### C. PostgreSQL no inicia

**Síntoma:** Error "could not connect to database"

**Solución (desde consola web):**
```bash
# Ver estado
systemctl status postgresql

# Ver logs de error
journalctl -u postgresql -n 50

# Reiniciar
systemctl restart postgresql

# Si falla, verificar espacio en disco
df -h

# Si el disco está lleno (>90%), limpiar logs antiguos
journalctl --vacuum-time=7d
```

### D. El servidor está lento o sin memoria

**Verificar recursos (desde consola web):**
```bash
# Ver uso de CPU y memoria
htop

# Ver procesos que más consumen
ps aux --sort=-%mem | head -10

# Ver espacio en disco
df -h

# Si hay poco espacio, limpiar logs
journalctl --vacuum-size=500M
```

---

## 📞 CHECKLIST RÁPIDO DE DIAGNÓSTICO

- [ ] ¿El droplet está encendido en DigitalOcean?
- [ ] ¿Puedes acceder via Consola Web?
- [ ] ¿El servicio `dragonbot` está activo?
- [ ] ¿PostgreSQL está corriendo?
- [ ] ¿Hay mensajes recientes en Telegram del bot?
- [ ] ¿Los logs muestran algún error específico?
- [ ] ¿El disco tiene espacio disponible?
- [ ] ¿La VPN está activa y conectada?

---

## 🆘 SI NADA FUNCIONA

1. **Desde el panel de DigitalOcean:**
   - Power Cycle (reinicio forzado)
   - Espera 5 minutos
   - Intenta acceder via consola web

2. **Si el droplet no enciende:**
   - Puede haber un problema de hardware
   - Contacta soporte de DigitalOcean

3. **Backup plan:**
   - Si tienes snapshot/backup del droplet
   - Restaura desde el backup
   - O crea un nuevo droplet y despliega de nuevo

---

## 📊 MONITOREO SIN SSH

Puedes verificar el bot **SIN NECESIDAD DE SSH**:

1. **Via Telegram:** Revisa si el bot envía mensajes
2. **Panel DigitalOcean:** Gráficas de CPU/RAM/Network
3. **Consola Web:** Acceso directo sin SSH

**El bot está diseñado para ser autónomo** - si envía mensajes a Telegram, está funcionando correctamente aunque no puedas conectarte por SSH.

---

## ⚡ COMANDO RÁPIDO PARA REINICIAR TODO

Si tienes acceso via consola web, ejecuta:

```bash
#!/bin/bash
echo "🔄 Reiniciando servicios..."
systemctl restart postgresql
sleep 5
systemctl restart fastestvpn
sleep 10
systemctl restart dragonbot
sleep 3
echo "✅ Servicios reiniciados. Verificando estado..."
systemctl status dragonbot --no-pager
```

Copia y pega todo el bloque en la consola web.
