# 🚀 Guía de Inicio Rápido

## ¡Bienvenido! 👋

Esta guía te explica **paso a paso** cómo descargar, instalar y ejecutar el Evolution Gaming Baccarat Scraper en tu computadora.

---

## 📋 Paso 1: ¿Qué necesitas antes de empezar?

Antes de descargar el proyecto, asegúrate de tener:

### ✅ Requisitos del Sistema

1. **Sistema Operativo**:
   - ✅ Windows 10/11
   - ✅ macOS 10.15 o superior
   - ✅ Linux (Ubuntu 20.04+, Debian, etc.)

2. **Python 3.10 o superior**:
   - Verifica si lo tienes: Abre una terminal/cmd y escribe:
     ```bash
     python --version
     ```
   - Si no lo tienes, descárgalo de: https://www.python.org/downloads/
   - ⚠️ En Windows, marca la casilla "Add Python to PATH" durante la instalación

3. **Git**:
   - Verifica si lo tienes:
     ```bash
     git --version
     ```
   - Si no lo tienes, descárgalo de: https://git-scm.com/downloads

4. **Cuenta en DragonSlots**:
   - Necesitas una cuenta activa en https://dragonslots-1.com
   - Anota tu **usuario** y **contraseña** (los necesitarás después)

5. **Telegram Bot Token** (opcional, para notificaciones):
   - Habla con [@BotFather](https://t.me/botfather) en Telegram
   - Sigue las instrucciones para crear un bot
   - Guarda el token que te dé

---

## 📥 Paso 2: Descargar el Proyecto

Tienes dos opciones:

### Opción A: Clonar con Git (recomendado)

1. Abre una terminal/cmd
2. Ve a la carpeta donde quieres guardar el proyecto:
   ```bash
   cd Desktop
   # O cualquier otra carpeta de tu preferencia
   ```

3. Clona el repositorio:
   ```bash
   git clone https://github.com/Midan14/EVOLUTION-SCRAPER.git
   ```

4. Entra a la carpeta del proyecto:
   ```bash
   cd EVOLUTION-SCRAPER
   ```

### Opción B: Descargar ZIP

1. Ve a: https://github.com/Midan14/EVOLUTION-SCRAPER
2. Click en el botón verde **"Code"**
3. Click en **"Download ZIP"**
4. Descomprime el archivo en tu computadora
5. Abre una terminal/cmd y ve a esa carpeta:
   ```bash
   cd ruta/donde/descomprimiste/EVOLUTION-SCRAPER
   ```

---

## ⚙️ Paso 3: Instalación

### 3.1 Crear un Entorno Virtual (recomendado)

Esto mantiene las dependencias del proyecto separadas:

**En Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**En macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

💡 **Nota**: Verás `(venv)` al inicio de tu línea de comandos cuando esté activado.

### 3.2 Instalar Dependencias de Python

```bash
pip install -r requirements.txt
```

⏱️ Esto puede tomar 2-5 minutos. Espera a que termine.

### 3.3 Instalar el Navegador Chromium

Este proyecto usa Playwright para controlar un navegador:

```bash
playwright install chromium
```

⏱️ Descargará ~150 MB. Espera a que termine.

---

## 🔐 Paso 4: Configurar tus Credenciales

### 4.1 Crear tu archivo de configuración

```bash
cp .env.example .env
```

**En Windows (si `cp` no funciona):**
```bash
copy .env.example .env
```

### 4.2 Editar el archivo .env

Abre el archivo `.env` con cualquier editor de texto (Notepad, VSCode, etc.) y completa:

```bash
# === CREDENCIALES DEL CASINO ===
CASINO_URL=https://dragonslots-1.com
CASINO_USERNAME=tu_usuario_aqui
CASINO_PASSWORD=tu_contraseña_aqui

# === CONFIGURACIÓN DEL JUEGO ===
GAME_URL=https://dragonslots-1.com/es/casino/game/evolution/xxxtremelightningbaccarat
GAME_TABLE_ID=xxxtremelightningbaccarat

# === CONFIGURACIÓN DEL NAVEGADOR ===
HEADLESS=false
# false = verás el navegador (recomendado para primera vez)
# true = navegador invisible (para servidor)

# === TELEGRAM (opcional) ===
TELEGRAM_BOT_TOKEN=tu_token_aqui
TELEGRAM_CHAT_ID=tu_chat_id_aqui

# === OTRAS CONFIGURACIONES ===
MIN_CONFIDENCE_TO_SEND=50
# Confianza mínima para enviar predicciones (0-100)
```

⚠️ **IMPORTANTE**: 
- Reemplaza `tu_usuario_aqui` y `tu_contraseña_aqui` con tus datos reales
- NO compartas este archivo con nadie (contiene tus credenciales)
- Si no tienes Telegram, puedes dejar esos campos vacíos

---

## 🎮 Paso 5: ¡Primera Ejecución!

### Opción 1: Modo Básico (Scraper + API)

Este es el modo más común. Inicia el scraper y un servidor API:

```bash
python run.py
```

Verás algo como:
```
🚀 Iniciando Evolution Gaming Baccarat Scraper...
✅ Base de datos conectada
🌐 Servidor API iniciado en http://0.0.0.0:8899
🔄 Navegador lanzado...
```

Ahora puedes:
- Ver la API en: http://localhost:8899/docs
- El navegador se abrirá y verás cómo se loguea automáticamente
- Los resultados se guardan en `data/results.db`

### Opción 2: Bot Inteligente con Telegram

Si configuraste Telegram y quieres predicciones:

```bash
python dragon_bot_ml.py
```

Este bot:
- ✅ Captura resultados en tiempo real
- 🧠 Usa Machine Learning para predecir
- 📊 Analiza patrones (gemelos, rachas, roads)
- 📱 Envía notificaciones a Telegram cuando encuentra oportunidades

### Opción 3: Solo API (sin scraper)

Si ya tienes datos y solo quieres el servidor API:

```bash
python run.py --api-only
```

### Opción 4: Modo Headless (sin ventana visible)

Para ejecutar en segundo plano:

```bash
python run.py --headless
```

---

## 🛠️ Solución de Problemas Comunes

### ❌ Error: "python: command not found"

**Solución**: Intenta con `python3` en lugar de `python`:
```bash
python3 run.py
```

### ❌ Error: "No module named 'playwright'"

**Solución**: El entorno virtual no está activado o las dependencias no se instalaron:
```bash
# Activa el entorno virtual primero
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Reinstala las dependencias
pip install -r requirements.txt
```

### ❌ Error: "playwright install chromium failed"

**Solución**: Puede que necesites permisos de administrador:

**Windows:** Abre cmd como Administrador

**macOS/Linux:**
```bash
sudo playwright install chromium
```

### ❌ Error: "Authentication failed" o "Login error"

**Solución**: 
1. Verifica que tu usuario y contraseña estén correctos en `.env`
2. Verifica que tu cuenta de DragonSlots esté activa
3. Intenta loguearte manualmente en https://dragonslots-1.com para asegurarte

### ❌ El navegador se cierra inmediatamente

**Solución**: Cambia en `.env`:
```bash
HEADLESS=false
```

### ❌ Error: "Address already in use" (puerto 8899)

**Solución**: Ya hay algo corriendo en ese puerto:

**Windows:**
```bash
netstat -ano | findstr :8899
taskkill /PID [número_del_pid] /F
```

**macOS/Linux:**
```bash
lsof -ti:8899 | xargs kill -9
```

---

## 📊 ¿Qué hace cada archivo?

| Archivo | ¿Qué hace? |
|---------|-----------|
| `run.py` | Inicia el scraper básico + API |
| `dragon_bot_ml.py` | Bot inteligente con ML y Telegram |
| `dragon_bot_advanced.py` | Versión avanzada (PostgreSQL) |
| `baccarat_strategies.py` | Estrategias de predicción |
| `data/results.db` | Base de datos con resultados capturados |
| `.env` | Tu configuración privada (credenciales) |

---

## 🎯 Próximos Pasos

Una vez que el proyecto esté corriendo:

1. **Ver los resultados capturados**:
   - Ve a http://localhost:8899/docs
   - Prueba el endpoint `/api/results` para ver los últimos resultados

2. **Ver estadísticas**:
   - Endpoint: `/api/statistics`
   - Te muestra % de Player/Banker/Tie

3. **Backtesting** (probar estrategias con datos históricos):
   ```bash
   python backtest_offline.py
   ```

4. **Análisis de patrones**:
   ```bash
   python road_analyzer.py
   ```

---

## 📚 Documentación Adicional

- **README.md** - Documentación técnica completa
- **STRUCTURE.md** - Estructura detallada del proyecto
- **CONTRIBUTING.md** - Si quieres contribuir al proyecto
- **SECURITY.md** - Buenas prácticas de seguridad
- **deploy/README.md** - Deploy en servidor 24/7

---

## 💬 ¿Necesitas Ayuda?

Si tienes problemas:

1. 📖 Lee **TROUBLESHOOTING_SERVIDOR.md** para problemas comunes
2. 🔍 Revisa los **logs** en la carpeta `logs/`
3. 📝 Abre un **Issue** en GitHub con tu problema
4. 📧 Contacta al mantenedor del proyecto

---

## ⚠️ Advertencias Importantes

1. **Privacidad**: Nunca compartas tu archivo `.env` (contiene tus credenciales)
2. **Términos de Servicio**: Este scraper puede violar los términos de servicio del casino
3. **Uso Responsable**: Este proyecto es solo para fines educativos y de investigación
4. **No apuesta**: El scraper solo observa, NO hace apuestas automáticas
5. **Responsabilidad**: Úsalo bajo tu propio riesgo

---

## ✨ ¡Todo Listo!

Si has seguido todos los pasos, el proyecto ya debería estar funcionando en tu computadora. 

**¡Disfruta explorando los datos de Baccarat!** 🎰📊

---

**Última actualización**: Febrero 2026  
**Versión**: 1.0
