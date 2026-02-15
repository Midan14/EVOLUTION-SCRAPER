# 🎰 Evolution Gaming Baccarat Scraper

Scraper para extraer resultados en tiempo real de mesas de Baccarat de Evolution Gaming.

---

## 🚀 ¿Primera vez? Lee la [Guía de Inicio Rápido](GUIA_INICIO_RAPIDO.md)

**Si eres nuevo** y quieres saber cómo descargar, instalar y ejecutar el proyecto paso a paso, **[haz clic aquí para ver la Guía de Inicio Rápido](GUIA_INICIO_RAPIDO.md)** 📖

---

## 🎯 Objetivo

Extraer datos de la mesa **XXXtreme Lightning Baccarat** de Evolution Gaming desde:
- URL: `https://dragonslots-1.com/es/casino/game/evolution/xxxtremelightningbaccarat`

## 🔧 Método de Extracción

Este scraper utiliza **Playwright** (automatización de navegador) para:

1. **Autenticarse** en el casino con credenciales de usuario
2. **Interceptar WebSocket/XHR** — Capturar mensajes del servidor de Evolution Gaming
3. **Extraer resultados** — Parsear los datos de cada ronda (Player/Banker/Tie, scores, etc.)
4. **Almacenar** — Guardar en base de datos SQLite y/o enviar a API externa
5. **Predecir** — Estrategias avanzadas de análisis (ML, gemelos, rachas, 4 roads)
6. **Notificar** — Enviar predicciones y resultados vía Telegram

## ⚠️ Requisitos Previos

1. **Cuenta en DragonSlots** — Necesitas una cuenta activa
2. **Python 3.10+**
3. **Playwright** instalado con Chromium

## 📦 Instalación

```bash
cd EVOLUTION-SCRAPER

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Instalar navegador Chromium para Playwright
playwright install chromium

# Configurar credenciales
cp .env.example .env
# Editar .env con tus credenciales
```

## 🧪 Desarrollo

```bash
pip install -r requirements-dev.txt

# Lint
ruff check .

# Tests
pytest -q

# Auditoría de seguridad
pip-audit -r requirements.txt
```

Para dependencias reproducibles usa `requirements.lock` (generado con `pip-compile` desde `requirements.in`).

## 🚀 Uso

### Scraper + API Server (modo recomendado)

```bash
python run.py
```

Esto levanta el scraper de Playwright y un servidor API en `http://0.0.0.0:8899`.

### Solo scraper (sin API)

```bash
python run.py --scraper-only
```

### Solo API (servir datos existentes)

```bash
python run.py --api-only
```

### Modo headless (sin ventana de navegador)

```bash
python run.py --headless
```

### Bot avanzado con ML + Telegram

```bash
python dragon_bot_ml.py
```

### Docker

```bash
docker compose up -d
```

## 📡 API Endpoints

Una vez levantado el servidor, la documentación interactiva está en `http://localhost:8899/docs`.

| Endpoint | Descripción |
|---|---|
| `GET /` | Información del servicio |
| `GET /health` | Estado de salud (DB, rounds capturados) |
| `GET /api/results` | Resultados recientes (parámetros: `limit`, `table_id`) |
| `GET /api/results/latest` | Último resultado |
| `GET /api/results/history` | Historial (formato `full` o `simple`) |
| `GET /api/statistics` | Estadísticas por período (`hours`) |
| `GET /api/streak` | Racha actual (Player/Banker) |
| `GET /api/pattern` | Patrón reciente para Big Road |
| `GET /api/roads` | Big Road y roads derivados |

## 📊 Estructura de Datos Extraídos

```json
{
    "round_id": "abc123",
    "timestamp": "2026-01-22T05:20:00Z",
    "result": "B",
    "player_score": 5,
    "banker_score": 7,
    "player_cards": ["♠A", "♥4"],
    "banker_cards": ["♦K", "♣7"],
    "lightning_cards": ["♠5", "♥8"],
    "multipliers": {"♠5": 2, "♥8": 5},
    "is_natural": false,
    "table_id": "xxxtremelightningbaccarat"
}
```

## 📁 Estructura del Proyecto

```
EVOLUTION-SCRAPER/
├── .env                          # Variables de entorno (NO subir a git)
├── .env.example                  # Plantilla de variables de entorno
├── .gitignore                    # Archivos excluidos de git
├── README.md                     # Este archivo
├── STRUCTURE.md                  # Documentación detallada de estructura
├── requirements.txt              # Dependencias Python
├── requirements.in               # Input para pip-compile
├── requirements.lock             # Dependencias pinned
├── requirements-dev.txt          # Dependencias de desarrollo
├── pyproject.toml                # Configuración de ruff y pytest
├── Dockerfile                    # Imagen Docker
├── docker-compose.yml            # Orquestación Docker
├── run.py                        # Punto de entrada principal
│
├── src/                          # Código fuente principal
│   ├── __init__.py
│   ├── config.py                 # Configuración (env vars)
│   ├── database.py               # Base de datos SQLite (async)
│   ├── scraper.py                # Scraper Playwright + interceptores WS
│   ├── api_server.py             # API REST (FastAPI)
│   └── api_scraper.py            # Scraper alternativo vía HTTP directo
│
├── tests/                        # Tests automatizados
│   ├── __init__.py
│   ├── test_scraper_extract.py   # Tests del scraper (extract, validate)
│   ├── test_api_server.py        # Tests de la API REST
│   └── test_database.py          # Tests de la base de datos
│
├── baccarat_strategies.py        # Estrategias de predicción (gemelos, rachas, etc.)
├── road_analyzer.py              # Análisis Big Road y roads derivados
├── advanced_agent.py             # Agente avanzado de análisis de mesa
├── dragon_bot_ml.py              # Bot con ML + Telegram
├── dragon_bot_advanced.py        # Bot avanzado (PostgreSQL)
├── telegram_notifier.py          # Notificaciones Telegram
├── backtest_offline.py           # Backtesting offline de estrategias
├── generate_test_data.py         # Generador de datos de prueba
├── test_ml_predictor.py          # Pruebas del predictor ML
│
├── deploy/                       # Scripts de despliegue en servidor
│   ├── README.md
│   ├── dragonbot.service         # Servicio systemd
│   ├── deploy_from_mac.sh        # Deploy desde Mac via rsync
│   ├── do_setup.sh               # Setup inicial del servidor
│   └── ...
│
├── ws_samples/                   # Muestras de mensajes WebSocket
│   ├── baccarat_newGame.json
│   ├── baccarat_gameState.json
│   ├── baccarat_resolved.json
│   ├── baccarat_tableState.json
│   └── baccarat_encodedShoeState.json
│
├── data/                         # Base de datos SQLite (generado)
│   └── results.db
├── logs/                         # Logs del scraper (generado)
│   └── scraper.log
├── browser_data/                 # Datos de sesión del navegador (generado)
└── .github/
    └── workflows/
        └── ci.yml                # CI: lint + tests + audit
```

## 🔒 Seguridad

- **NO** compartir credenciales — usa `.env` (incluido en `.gitignore`)
- Variables sensibles cargadas desde variables de entorno
- `storage_state.json` contiene cookies de sesión — nunca subir a git
- CORS del API configurable vía `CORS_ORIGINS` en `.env`
- El scraper **NO** apuesta, solo observa

## 🐳 Docker

```bash
# Construir y ejecutar
docker compose up -d

# Ver logs
docker compose logs -f scraper

# Health check
curl http://localhost:8899/health
```

## 🚀 Deploy en Servidor (DigitalOcean)

Ver `deploy/README.md` para instrucciones detalladas de despliegue 24/7 con systemd.

```bash
# Desde tu Mac
bash deploy/deploy_from_mac.sh
```

## ⚖️ Disclaimer

Este proyecto es solo para fines educativos y de investigación.
El uso de scrapers puede violar los términos de servicio de los casinos.
Úsalo bajo tu propia responsabilidad.