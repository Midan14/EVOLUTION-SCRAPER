# Estructura del proyecto EVOLUTION-SCRAPER

Ruta base: `/Users/miguelantonio/Desktop/EVOLUTION-SCRAPER`  
(o `./` desde la raíz del proyecto)

---

## Raíz del proyecto

| Archivo | Ruta completa | Descripción |
|--------|----------------|-------------|
| `.env` | `EVOLUTION-SCRAPER/.env` | Variables de entorno (credenciales, Telegram). No subir a Git. |
| `.env.example` | `EVOLUTION-SCRAPER/.env.example` | Plantilla de variables de entorno. |
| `README.md` | `EVOLUTION-SCRAPER/README.md` | Documentación principal del proyecto. |
| `requirements.txt` | `EVOLUTION-SCRAPER/requirements.txt` | Dependencias de Python. |
| `dragon_bot_ml.py` | `EVOLUTION-SCRAPER/dragon_bot_ml.py` | **Bot principal**: Playwright + estrategias + Telegram. |
| `dragon_bot_advanced.py` | `EVOLUTION-SCRAPER/dragon_bot_advanced.py` | Versión avanzada del bot (alternativa). |
| `baccarat_strategies.py` | `EVOLUTION-SCRAPER/baccarat_strategies.py` | Lógica de estrategias (Memoria, Gemelos, Rachas, Scores, 4 Roads). |
| `road_analyzer.py` | `EVOLUTION-SCRAPER/road_analyzer.py` | Análisis y construcción de Big Road y roads derivados. |
| `telegram_notifier.py` | `EVOLUTION-SCRAPER/telegram_notifier.py` | Envío de notificaciones a Telegram. |
| `get_chat_id.py` | `EVOLUTION-SCRAPER/get_chat_id.py` | Script para obtener el ID de chat de Telegram. |
| `capture_evolution.py` | `EVOLUTION-SCRAPER/capture_evolution.py` | Script de captura original (Evolution). |
| `capture_with_auth.py` | `EVOLUTION-SCRAPER/capture_with_auth.py` | Captura WebSocket con autenticación. |
| `ws_capture.py` | `EVOLUTION-SCRAPER/ws_capture.py` | Captura de mensajes WebSocket. |
| `save_storage_state.py` | `EVOLUTION-SCRAPER/save_storage_state.py` | Guarda estado de sesión de Playwright. |
| `run.py` | `EVOLUTION-SCRAPER/run.py` | Punto de entrada alternativo de ejecución. |
| `load_historical_data.py` | `EVOLUTION-SCRAPER/load_historical_data.py` | Carga de datos históricos. |
| `touch generate_test_data.py` | `EVOLUTION-SCRAPER/touch generate_test_data.py` | Generador de datos de prueba. |
| `touch test_ml_predictor.py` | `EVOLUTION-SCRAPER/touch test_ml_predictor.py` | Pruebas del predictor ML. |
| `storage_state.json` | `EVOLUTION-SCRAPER/storage_state.json` | Estado de sesión del navegador (cookies, etc.). |
| `storage_state.ready` | `EVOLUTION-SCRAPER/storage_state.ready` | Indicador de sesión lista. |
| `captured_formatted.json` | `EVOLUTION-SCRAPER/captured_formatted.json` | Respuestas capturadas (formato). |
| `captured_responses.json` | `EVOLUTION-SCRAPER/captured_responses.json` | Respuestas capturadas (raw). |
| `websocket_messages.json` | `EVOLUTION-SCRAPER/websocket_messages.json` | Mensajes WebSocket de ejemplo. |
| `docker-compose.yml` | `EVOLUTION-SCRAPER/docker-compose.yml` | Configuración Docker Compose. |
| `Dockerfile` | `EVOLUTION-SCRAPER/Dockerfile` | Imagen Docker de la aplicación. |

---

## Carpeta `data/`

| Archivo | Ruta completa | Descripción |
|--------|----------------|-------------|
| `results.db` | `EVOLUTION-SCRAPER/data/results.db` | Base de datos SQLite (resultados). |

---

## Carpeta `deploy/`

| Archivo | Ruta completa | Descripción |
|--------|----------------|-------------|
| `README.md` | `EVOLUTION-SCRAPER/deploy/README.md` | Documentación de despliegue 24/7 e IP del droplet (165.232.142.48). |
| `deploy_from_mac.sh` | `EVOLUTION-SCRAPER/deploy/deploy_from_mac.sh` | Sube el proyecto al servidor desde tu Mac (rsync + opción de reiniciar servicio). |
| `do_setup.sh` | `EVOLUTION-SCRAPER/deploy/do_setup.sh` | Script de configuración inicial en el servidor (PostgreSQL, venv, Playwright). |
| `dragonbot.service` | `EVOLUTION-SCRAPER/deploy/dragonbot.service` | Unidad systemd para ejecutar el bot 24/7 en modo headless. |

---

## Carpeta `logs/`

| Archivo | Ruta completa | Descripción |
|--------|----------------|-------------|
| `scraper.log` | `EVOLUTION-SCRAPER/logs/scraper.log` | Log del scraper/bot. |

---

## Carpeta `src/`

| Archivo | Ruta completa | Descripción |
|--------|----------------|-------------|
| `config.py` | `EVOLUTION-SCRAPER/src/config.py` | Configuración de la aplicación. |
| `database.py` | `EVOLUTION-SCRAPER/src/database.py` | Acceso a base de datos. |
| `scraper.py` | `EVOLUTION-SCRAPER/src/scraper.py` | Lógica del scraper (Playwright/API). |
| `api_scraper.py` | `EVOLUTION-SCRAPER/src/api_scraper.py` | Scraper vía API. |
| `api_server.py` | `EVOLUTION-SCRAPER/src/api_server.py` | Servidor API. |

---

## Carpeta `ws_samples/`

| Archivo | Ruta completa | Descripción |
|--------|----------------|-------------|
| `baccarat_newGame.json` | `EVOLUTION-SCRAPER/ws_samples/baccarat_newGame.json` | Muestra: nuevo juego. |
| `baccarat_gameState.json` | `EVOLUTION-SCRAPER/ws_samples/baccarat_gameState.json` | Muestra: estado de juego. |
| `baccarat_resolved.json` | `EVOLUTION-SCRAPER/ws_samples/baccarat_resolved.json` | Muestra: ronda resuelta. |
| `baccarat_tableState.json` | `EVOLUTION-SCRAPER/ws_samples/baccarat_tableState.json` | Muestra: estado de mesa. |
| `baccarat_encodedShoeState.json` | `EVOLUTION-SCRAPER/ws_samples/baccarat_encodedShoeState.json` | Muestra: zapato codificado. |

---

## Carpetas generadas / no versionadas

| Carpeta | Ruta completa | Descripción |
|--------|----------------|-------------|
| `browser_data/` | `EVOLUTION-SCRAPER/browser_data/` | Datos de sesión del navegador (caché, cookies, IndexedDB). |
| `venv/` | `EVOLUTION-SCRAPER/venv/` | Entorno virtual de Python. |
| `.mypy_cache/` | `EVOLUTION-SCRAPER/.mypy_cache/` | Caché de mypy (type checker). |

---

## Resumen en árbol

```
EVOLUTION-SCRAPER/
├── .env
├── .env.example
├── README.md
├── STRUCTURE.md
├── requirements.txt
├── dragon_bot_ml.py
├── dragon_bot_advanced.py
├── baccarat_strategies.py
├── road_analyzer.py
├── telegram_notifier.py
├── get_chat_id.py
├── capture_evolution.py
├── capture_with_auth.py
├── ws_capture.py
├── save_storage_state.py
├── run.py
├── load_historical_data.py
├── touch generate_test_data.py
├── touch test_ml_predictor.py
├── storage_state.json
├── storage_state.ready
├── captured_formatted.json
├── captured_responses.json
├── websocket_messages.json
├── docker-compose.yml
├── Dockerfile
├── data/
│   └── results.db
├── deploy/
│   ├── README.md
│   ├── deploy_from_mac.sh
│   ├── do_setup.sh
│   └── dragonbot.service
├── logs/
│   └── scraper.log
├── src/
│   ├── api_scraper.py
│   ├── api_server.py
│   ├── config.py
│   ├── database.py
│   └── scraper.py
├── ws_samples/
│   ├── baccarat_encodedShoeState.json
│   ├── baccarat_gameState.json
│   ├── baccarat_newGame.json
│   ├── baccarat_resolved.json
│   └── baccarat_tableState.json
├── browser_data/   (generado)
├── venv/           (entorno virtual)
└── .mypy_cache/    (caché)
```
