#!/usr/bin/env python3
"""
Evolution Gaming Baccarat Scraper
Extracts real-time results from XXXtreme Lightning Baccarat

Uses Playwright to:
1. Authenticate with casino
2. Navigate to game
3. Intercept WebSocket/XHR messages containing game results
"""
import asyncio
import json
import logging
import re
import signal
import struct
import sys
import traceback
import zlib
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import aiohttp
from playwright.async_api import BrowserContext, Page, Request, Route, WebSocket, async_playwright

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from config import config
from database import db

Path(config.LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

# Configure logging (rotate daily, keep 7 days)
log_handlers = [
    logging.StreamHandler(),
    TimedRotatingFileHandler(config.LOG_FILE, when="midnight", backupCount=7, encoding="utf-8"),
]
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s | %(levelname)-8s | pid=%(process)d | %(message)s',
    handlers=log_handlers
)
logger = logging.getLogger(__name__)

# Patterns that indicate a request is related to Evolution Gaming
_EVOLUTION_URL_KEYWORDS = ('evolution', 'evo-', '/game/', '/round/', '/result/')


class EvolutionScraper:
    """
    Scraper for Evolution Gaming Baccarat tables

    Strategy:
    - Uses Playwright to control a real browser session
    - Intercepts WebSocket messages from Evolution servers
    - Parses game results from the intercepted data
    - Stores results in SQLite database
    """

    def __init__(self):
        self.browser = None
        self.playwright = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.running = False
        self.rounds_captured = 0
        self.last_round_id: Optional[str] = None
        self.websocket_connections: list = []
        self.on_result_callback: Optional[Callable] = None
        self.last_frame_at: Optional[datetime] = None
        self.last_session_refresh_at: Optional[datetime] = None
        self.black_screen_consecutive_hits = 0

    def _build_context_kwargs(self) -> Dict[str, Any]:
        """Build browser context args, avoiding bot-signature UA patterns."""
        storage_state_path = (
            Path(config.STORAGE_STATE_PATH) if hasattr(config, 'STORAGE_STATE_PATH') else None
        )
        kwargs: Dict[str, Any] = {
            "viewport": {'width': config.VIEWPORT_WIDTH, 'height': config.VIEWPORT_HEIGHT},
            "locale": 'es-ES',
            "timezone_id": 'America/Mexico_City',
            "storage_state": (
                str(storage_state_path)
                if storage_state_path and storage_state_path.exists()
                else None
            ),
        }

        user_agent = (getattr(config, "USER_AGENT", "") or "").strip().strip('"').strip("'")
        if user_agent:
            if re.search(r"Chrome/\d+\.0\.0\.0", user_agent):
                logger.warning(
                    "⚠️ Ignoring USER_AGENT with bot-like Chrome pattern (x.0.0.0)"
                )
            else:
                kwargs["user_agent"] = user_agent

        return kwargs

    def _browser_launch_args(self) -> list[str]:
        return [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--autoplay-policy=no-user-gesture-required',
            '--use-angle=metal',
            '--enable-gpu-rasterization',
            '--ignore-gpu-blocklist',
            '--enable-zero-copy',
            '--disable-features=PreloadMediaEngagementData,MediaEngagementBypassAutoplayPolicies',
        ]

    def _stealth_init_script(self) -> str:
        return """
            // Override navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

            // Override chrome
            window.chrome = {runtime: {}};

            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );

            // Capture JS errors for diagnostics
            window.__scraperErrors = [];
            window.addEventListener('error', (event) => {
                try {
                    window.__scraperErrors.push(String(event.message || 'unknown'));
                    if (window.__scraperErrors.length > 20) {
                        window.__scraperErrors = window.__scraperErrors.slice(-20);
                    }
                } catch (e) {}
            });
            window.addEventListener('unhandledrejection', (event) => {
                try {
                    const reason = event && event.reason ? String(event.reason) : 'unknown rejection';
                    window.__scraperErrors.push(reason);
                    if (window.__scraperErrors.length > 20) {
                        window.__scraperErrors = window.__scraperErrors.slice(-20);
                    }
                } catch (e) {}
            });
        """

    async def _launch_browser(self):
        """Launch browser with optional channel and safe fallback."""
        launch_kwargs: Dict[str, Any] = {
            "headless": config.HEADLESS,
            "slow_mo": config.SLOW_MO,
            "args": self._browser_launch_args(),
        }
        if config.BROWSER_CHANNEL:
            launch_kwargs["channel"] = config.BROWSER_CHANNEL
            logger.info(f"🧭 Browser channel requested: {config.BROWSER_CHANNEL}")

        try:
            # Usar Chrome si está configurado, sino Chromium
            if config.BROWSER_CHANNEL == "chrome":
                return await self.playwright.chromium.launch(channel="chrome", **{
                    k: v for k, v in launch_kwargs.items() if k != "channel"
                })
            return await self.playwright.chromium.launch(**launch_kwargs)
        except Exception as e:
            if config.BROWSER_CHANNEL:
                logger.warning(
                    f"Could not launch channel '{config.BROWSER_CHANNEL}': {e}. "
                    "Falling back to bundled Chromium."
                )
                launch_kwargs.pop("channel", None)
                return await self.playwright.chromium.launch(**launch_kwargs)
            raise

    async def start(self):
        """Start the scraper"""
        logger.info("=" * 60)
        logger.info("🎰 EVOLUTION GAMING BACCARAT SCRAPER")
        logger.info("=" * 60)
        logger.info(f"Target: {config.GAME_URL}")
        logger.info(f"Headless: {config.HEADLESS}")

        # Connect to database
        await db.connect()

        # Launch browser
        self.playwright = await async_playwright().start()

        self.browser = await self._launch_browser()

        # Create context with anti-detection measures
        self.context = await self.browser.new_context(**self._build_context_kwargs())

        # Add stealth scripts
        await self.context.add_init_script(self._stealth_init_script())

        self.page = await self.context.new_page()

        # Setup interceptors
        await self._setup_interceptors()

        self.running = True
        self.last_session_refresh_at = datetime.now(timezone.utc)
        logger.info("✅ Browser launched successfully")

    async def _ensure_page_available(self):
        """Ensure browser/context/page are alive before navigation actions."""
        if not self.playwright:
            self.playwright = await async_playwright().start()

        if not self.browser or not self.browser.is_connected():
            self.browser = await self._launch_browser()

        if not self.context:
            self.context = await self.browser.new_context(**self._build_context_kwargs())

            await self.context.add_init_script(self._stealth_init_script())

        if not self.page or self.page.is_closed():
            self.page = await self.context.new_page()
            await self._setup_interceptors()
            logger.info("✅ Browser page recreated")

    async def _setup_interceptors(self):
        """Setup WebSocket and XHR interceptors"""

        # Intercept WebSocket connections
        self.page.on('websocket', self._on_websocket)

        # Intercept XHR/Fetch requests
        await self.page.route('**/*', self._on_request)

        # Log console messages for debugging
        self.page.on('console', lambda msg: logger.debug(f"[CONSOLE] {msg.text}"))

        logger.info("✅ Interceptors configured")

    def _on_websocket(self, ws: WebSocket):
        """Handle new WebSocket connection"""
        logger.info(f"🔌 WebSocket connected: {ws.url}")
        self.websocket_connections.append(ws)

        def _handle_frame(payload):
            try:
                asyncio.create_task(self._on_ws_message(ws.url, payload))
            except Exception as exc:
                logger.error(f"Failed to schedule WS message task: {exc}")

        # Listen for messages
        ws.on('framereceived', _handle_frame)

        ws.on('close', lambda: self._on_ws_close(ws))
        ws.on(
            'socketerror',
            lambda err: logger.error(f"🔌 WebSocket error on {ws.url}: {err}"),
        )

    def _on_ws_close(self, ws: WebSocket):
        """Handle WebSocket disconnection"""
        logger.warning(f"🔌 WebSocket closed: {ws.url}")
        if ws in self.websocket_connections:
            self.websocket_connections.remove(ws)
        active = len(self.websocket_connections)
        logger.info(f"   Active WebSocket connections remaining: {active}")
        if active == 0:
            logger.warning(
                "⚠️ No active WebSocket connections"
                " — will attempt reconnect on next stale check"
            )

    async def _on_ws_message(self, url: str, payload: dict):
        """Process WebSocket message"""
        try:
            self.last_frame_at = datetime.now(timezone.utc)
            db.last_frame_at = self.last_frame_at.isoformat()
            # Robust handling for different payload types (str, bytes, dict, other)
            try:
                payload_type = type(payload).__name__
                logger.debug(f"WS payload type: {payload_type}")
            except Exception:
                payload_type = str(type(payload))

            if isinstance(payload, bytes):
                try:
                    data = payload.decode('utf-8', errors='ignore')
                except Exception:
                    data = str(payload)
            elif isinstance(payload, str):
                data = payload
            elif isinstance(payload, dict):
                data = payload.get('payload', '') if payload.get('payload', None) is not None else str(payload)
            else:
                # Fallback: stringify payload
                try:
                    data = str(payload)
                except Exception:
                    data = ''

            # Try to parse as JSON
            if isinstance(data, str):
                # Evolution uses various message formats
                # Look for game result patterns
                data_lower = data.lower()
                if any(keyword in data_lower for keyword in [
                    'result', 'winner', 'player', 'banker', 'tie',
                    'roundresult', 'gameresult', 'baccarat'
                ]):
                    logger.debug(f"📨 Potential result message: {data[:200]}...")
                    await self._parse_evolution_message(data)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Error processing WS message: {e}\n{traceback.format_exc()}")

    async def _on_request(self, route: Route, request: Request):
        """Intercept HTTP requests without breaking provider iframe/media loading."""
        url = request.url
        url_lower = url.lower()
        resource_type = request.resource_type

        # Fast path: let non-Evolution requests pass through immediately
        if not any(kw in url_lower for kw in _EVOLUTION_URL_KEYWORDS):
            await route.continue_()
            return

        # Never proxy/fulfill document/iframe/script/media requests for provider pages.
        # Intercepting these can cause black screen in embedded game clients.
        if resource_type not in {'xhr', 'fetch'}:
            await route.continue_()
            return

        logger.debug(f"📡 Request intercepted: {url[:120]}")

        try:
            # Continue the request and capture response
            response = await route.fetch()
            
            # Only try to read text for text-based responses
            content_type = response.headers.get('content-type', '').lower()
            if 'text/' in content_type or 'application/json' in content_type or 'application/javascript' in content_type:
                body = await response.text()
                
                # Check if response contains game data
                if response.ok and body:
                    await self._parse_api_response(url, body)
            else:
                # Skip binary responses (images, etc.)
                logger.debug(f"Skipping binary response: {content_type}")

            await route.fulfill(response=response)
        except Exception as e:
            logger.warning(f"Error intercepting request {url[:80]}: {e}")
            # Don't block the page — let the request continue normally
            try:
                await route.continue_()
            except Exception:
                pass

    async def _parse_evolution_message(self, data: str):
        """Parse Evolution Gaming message for results"""
        try:
            # Try JSON parse
            try:
                msg = json.loads(data)
            except (json.JSONDecodeError, ValueError):
                # Try to extract JSON from message
                json_match = re.search(r'\{.*\}', data, re.DOTALL)
                if json_match:
                    msg = json.loads(json_match.group())
                else:
                    return

            # Look for result data in various Evolution message formats
            result = self._extract_baccarat_result(msg)

            if result and result.get('round_id') != self.last_round_id:
                self.last_round_id = result['round_id']
                await self._process_result(result)

        except Exception as e:
            logger.debug(f"Could not parse message: {e}")

    async def _parse_api_response(self, url: str, body: str):
        """Parse API response for results"""
        try:
            data = json.loads(body)
            result = self._extract_baccarat_result(data)

            if result and result.get('round_id') != self.last_round_id:
                self.last_round_id = result['round_id']
                await self._process_result(result)

        except Exception as e:
            logger.debug(f"Could not parse API response: {e}")

    def _extract_baccarat_result(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract baccarat result from Evolution message

        Evolution uses various message formats, we try to handle common patterns:
        - Direct result objects
        - Nested in 'data', 'result', 'gameResult' etc.
        """
        if not isinstance(data, dict):
            return None

        # Try different data paths
        result_data = None
        for path in ['result', 'data', 'gameResult', 'roundResult', 'payload']:
            if path in data and isinstance(data[path], dict):
                result_data = data[path]
                break

        if not result_data:
            result_data = data

        # Look for winner indicator
        winner = None
        for key in ['winner', 'outcome', 'result', 'winningHand']:
            if key in result_data:
                val = str(result_data[key]).upper()
                if 'PLAYER' in val or val == 'P':
                    winner = 'P'
                elif 'BANKER' in val or val == 'B':
                    winner = 'B'
                elif 'TIE' in val or val == 'T':
                    winner = 'T'
                break

        if not winner:
            return None

        # Extract round ID
        round_id = None
        for key in ['roundId', 'round_id', 'gameId', 'id', 'roundNumber']:
            if key in result_data:
                round_id = str(result_data[key])
                break

        if not round_id:
            round_id = f"evo_{datetime.now().timestamp()}"

        # Extract scores
        player_score = None
        banker_score = None

        for key in ['playerScore', 'player_score', 'playerTotal', 'playerPoints']:
            if key in result_data:
                try:
                    player_score = int(result_data[key])
                except (TypeError, ValueError):
                    player_score = None
                break

        for key in ['bankerScore', 'banker_score', 'bankerTotal', 'bankerPoints']:
            if key in result_data:
                try:
                    banker_score = int(result_data[key])
                except (TypeError, ValueError):
                    banker_score = None
                break

        # Extract cards (if available)
        player_cards = result_data.get('playerCards', result_data.get('player_cards', []))
        banker_cards = result_data.get('bankerCards', result_data.get('banker_cards', []))
        
        # Extract pair data
        player_pair = result_data.get('playerPair', result_data.get('player_pair', False))
        banker_pair = result_data.get('bankerPair', result_data.get('banker_pair', False))
        
        # Lightning specific data
        lightning_cards = result_data.get('lightningCards', result_data.get('lightning_cards', []))
        multipliers = result_data.get('multipliers', result_data.get('lightningMultipliers', {}))

        is_natural = False
        if player_score is not None and banker_score is not None:
            is_natural = (player_score in [8, 9]) or (banker_score in [8, 9])

        return {
            'round_id': round_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'result': winner,
            'player_score': player_score,
            'banker_score': banker_score,
            'player_cards': player_cards,
            'banker_cards': banker_cards,
            'player_pair': player_pair,
            'banker_pair': banker_pair,
            'lightning_cards': lightning_cards,
            'multipliers': multipliers,
            'table_id': config.GAME_TABLE_ID,
            'is_natural': is_natural,
            'raw_data': result_data
        }

    def _validate_result(self, result: Dict[str, Any]) -> bool:
        if not result.get('round_id') or not result.get('result'):
            return False
        if result.get('result') not in {'P', 'B', 'T'}:
            return False
        return True

    async def _process_result(self, result: Dict[str, Any]):
        """Process and store a new result"""
        if not self._validate_result(result):
            logger.warning(f"⚠️ Invalid result skipped: {result}")
            return
        self.rounds_captured += 1

        # Log result
        emoji = {'P': '🔵', 'B': '🔴', 'T': '🟢'}
        logger.info(
            f"{emoji.get(result['result'], '⚪')} RESULT: {result['result']} | "
            f"P:{result.get('player_score', '?')} vs B:{result.get('banker_score', '?')} | "
            f"Round: {result['round_id']}"
        )

        # Save to database
        await db.insert_result(result)

        # Call callback if set
        if self.on_result_callback:
            await self.on_result_callback(result)

        # Send webhook if enabled
        if config.WEBHOOK_ENABLED and config.WEBHOOK_URL:
            await self._send_webhook(result)

    async def _send_webhook(self, result: Dict[str, Any]):
        """Send result to webhook URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    config.WEBHOOK_URL,
                    json=result,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        logger.debug("Webhook sent successfully")
                    else:
                        logger.warning(f"Webhook failed: {resp.status}")
        except Exception as e:
            logger.error(f"Webhook error: {e}")

    def _score_frame_url(self, url: str) -> int:
        url = (url or "").lower()
        if "a8r.evo-games.com" in url:
            return 120
        if "evo-games.com" in url:
            return 100
        if "evolution" in url or "baccarat" in url:
            return 80
        if "ignition.button" in url:
            return 40
        if "livechat" in url or "recaptcha" in url:
            return -100
        return 0

    async def _find_game_frame(self):
        """Find most likely game frame among all nested frames (excluding main frame)."""
        if not self.page:
            return None
        try:
            best_frame = None
            best_score = float("-inf")
            for frame in self.page.frames:
                if frame == self.page.main_frame:
                    continue
                score = float(self._score_frame_url(frame.url))
                if score <= -100:
                    continue

                # Prefer frames that actually expose game-like surfaces.
                try:
                    signals = await frame.evaluate("""
                        () => ({
                            hasCanvas: !!document.querySelector('canvas'),
                            hasVideo: !!document.querySelector('video'),
                            textLen: (document.body && document.body.innerText ? document.body.innerText.trim().length : 0)
                        })
                    """)
                    if signals.get("hasCanvas"):
                        score += 60
                    if signals.get("hasVideo"):
                        score += 40
                    if signals.get("textLen", 0) > 0:
                        score += 5
                except Exception:
                    pass

                # Prefer larger visible frames.
                try:
                    frame_el = await frame.frame_element()
                    box = await frame_el.bounding_box()
                    if box:
                        area = float(box.get("width", 0.0)) * float(box.get("height", 0.0))
                        score += min(area / 100000.0, 30.0)
                except Exception:
                    pass

                if score > best_score:
                    best_score = score
                    best_frame = frame
            return best_frame
        except Exception:
            pass
        return None

    async def _find_game_iframe_element(self):
        """Find iframe element associated with the selected game frame."""
        if not self.page:
            return None
        try:
            frame = await self._find_game_frame()
            if frame:
                return await frame.frame_element()
        except Exception:
            pass

        # Fallback: largest visible iframe.
        try:
            iframes = await self.page.query_selector_all("iframe")
            best_iframe = None
            best_area = 0.0
            for iframe in iframes:
                box = await iframe.bounding_box()
                if not box:
                    continue
                width = float(box.get("width", 0.0))
                height = float(box.get("height", 0.0))
                area = width * height
                if area > best_area and width >= 300 and height >= 180:
                    best_area = area
                    best_iframe = iframe
            return best_iframe
        except Exception:
            return None

    async def inspect_game_render_state(self) -> Dict[str, Any]:
        """Inspect render/video/webgl state in page and game frame."""
        diag: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "page_url": self.page.url if self.page else None,
            "visibility_state": None,
            "viewport": {},
            "iframe_found": False,
            "frame_url": None,
            "has_canvas": False,
            "has_video": False,
            "video_state": {},
            "webgl": {"webgl": False, "webgl2": False},
            "errors": [],
        }

        if not config.RENDER_DIAG_ENABLED or not self.page:
            return diag

        try:
            page_diag = await self.page.evaluate("""
                () => {
                    const errors = Array.isArray(window.__scraperErrors) ? window.__scraperErrors.slice(-10) : [];
                    return {
                        visibilityState: document.visibilityState || null,
                        viewport: { width: window.innerWidth || 0, height: window.innerHeight || 0 },
                        errors
                    };
                }
            """)
            diag["visibility_state"] = page_diag.get("visibilityState")
            diag["viewport"] = page_diag.get("viewport") or {}
            diag["errors"] = page_diag.get("errors") or []
        except Exception as e:
            diag["errors"].append(f"page-eval: {e}")

        frame = await self._find_game_frame()
        if not frame:
            logger.info(f"RENDER_DIAG: {json.dumps(diag, ensure_ascii=False, default=str)}")
            return diag

        diag["iframe_found"] = True
        diag["frame_url"] = frame.url
        try:
            frame_diag = await frame.evaluate("""
                () => {
                    const out = {
                        hasCanvas: false,
                        hasVideo: false,
                        videoState: {},
                        webgl: { webgl: false, webgl2: false },
                        errors: [],
                        viewport: { width: window.innerWidth || 0, height: window.innerHeight || 0 },
                        visibilityState: document.visibilityState || null
                    };
                    try {
                        const canvas = document.querySelector('canvas');
                        const video = document.querySelector('video');
                        out.hasCanvas = !!canvas;
                        out.hasVideo = !!video;
                        if (video) {
                            out.videoState = {
                                readyState: video.readyState,
                                paused: !!video.paused,
                                muted: !!video.muted,
                                currentTime: Number(video.currentTime || 0),
                                width: Number(video.videoWidth || 0),
                                height: Number(video.videoHeight || 0)
                            };
                        }
                        if (canvas) {
                            try { out.webgl.webgl = !!(canvas.getContext('webgl') || canvas.getContext('experimental-webgl')); } catch (e) {}
                            try { out.webgl.webgl2 = !!canvas.getContext('webgl2'); } catch (e) {}
                        }
                        if (Array.isArray(window.__scraperErrors)) {
                            out.errors = window.__scraperErrors.slice(-10);
                        }
                    } catch (e) {
                        out.errors.push(String(e));
                    }
                    return out;
                }
            """)
            diag["has_canvas"] = bool(frame_diag.get("hasCanvas"))
            diag["has_video"] = bool(frame_diag.get("hasVideo"))
            diag["video_state"] = frame_diag.get("videoState") or {}
            diag["webgl"] = frame_diag.get("webgl") or {"webgl": False, "webgl2": False}
            diag["errors"] = (diag.get("errors") or []) + (frame_diag.get("errors") or [])
            if frame_diag.get("viewport"):
                diag["viewport"] = frame_diag.get("viewport")
            if frame_diag.get("visibilityState"):
                diag["visibility_state"] = frame_diag.get("visibilityState")
        except Exception as e:
            diag["errors"] = (diag.get("errors") or []) + [f"frame-eval: {e}"]

        logger.info(f"RENDER_DIAG: {json.dumps(diag, ensure_ascii=False, default=str)}")
        return diag

    def _png_dark_ratio(self, png_bytes: bytes) -> Optional[float]:
        """Compute dark pixel ratio from PNG bytes (supports RGB/RGBA 8-bit)."""
        try:
            if not png_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
                return None

            pos = 8
            width = height = 0
            color_type = None
            bit_depth = None
            compressed = b""

            while pos + 8 <= len(png_bytes):
                length = struct.unpack(">I", png_bytes[pos:pos + 4])[0]
                pos += 4
                chunk_type = png_bytes[pos:pos + 4]
                pos += 4
                data = png_bytes[pos:pos + length]
                pos += length
                pos += 4  # CRC

                if chunk_type == b"IHDR":
                    width, height, bit_depth, color_type = struct.unpack(">IIBB", data[:10])
                elif chunk_type == b"IDAT":
                    compressed += data
                elif chunk_type == b"IEND":
                    break

            if not width or not height or bit_depth != 8:
                return None
            if color_type not in (2, 6):  # RGB or RGBA
                return None

            raw = zlib.decompress(compressed)
            bpp = 3 if color_type == 2 else 4
            stride = width * bpp
            i = 0
            prev = bytearray(stride)
            dark = 0
            total = width * height

            for _ in range(height):
                filter_type = raw[i]
                i += 1
                scan = bytearray(raw[i:i + stride])
                i += stride

                if filter_type == 1:  # Sub
                    for x in range(bpp, stride):
                        scan[x] = (scan[x] + scan[x - bpp]) & 0xFF
                elif filter_type == 2:  # Up
                    for x in range(stride):
                        scan[x] = (scan[x] + prev[x]) & 0xFF
                elif filter_type == 3:  # Average
                    for x in range(stride):
                        left = scan[x - bpp] if x >= bpp else 0
                        up = prev[x]
                        scan[x] = (scan[x] + ((left + up) >> 1)) & 0xFF
                elif filter_type == 4:  # Paeth
                    def paeth(a: int, b: int, c: int) -> int:
                        p = a + b - c
                        pa = abs(p - a)
                        pb = abs(p - b)
                        pc = abs(p - c)
                        if pa <= pb and pa <= pc:
                            return a
                        if pb <= pc:
                            return b
                        return c

                    for x in range(stride):
                        a = scan[x - bpp] if x >= bpp else 0
                        b = prev[x]
                        c = prev[x - bpp] if x >= bpp else 0
                        scan[x] = (scan[x] + paeth(a, b, c)) & 0xFF

                for x in range(0, stride, bpp):
                    r = scan[x]
                    g = scan[x + 1]
                    b = scan[x + 2]
                    if r <= 20 and g <= 20 and b <= 20:
                        dark += 1
                prev = scan

            return dark / total if total else None
        except Exception:
            return None

    async def is_game_black_screen(self) -> bool:
        """Determine if game area is mostly black in two consecutive checks."""
        if not config.BLACK_SCREEN_CHECK_ENABLED or not self.page:
            return False

        async def _capture_dark_ratio() -> Optional[float]:
            try:
                iframe = await self._find_game_iframe_element()
                if iframe:
                    box = await iframe.bounding_box()
                    if box and box.get("width", 0) > 0 and box.get("height", 0) > 0:
                        png = await self.page.screenshot(
                            type="png",
                            clip={
                                "x": box["x"],
                                "y": box["y"],
                                "width": box["width"],
                                "height": box["height"],
                            },
                        )
                        return self._png_dark_ratio(png)

                png = await self.page.screenshot(type="png")
                return self._png_dark_ratio(png)
            except Exception as e:
                logger.warning(f"Could not capture screenshot for black-screen check: {e}")
                return None

        ratio1 = await _capture_dark_ratio()
        if ratio1 is None:
            return False
        await asyncio.sleep(1)
        ratio2 = await _capture_dark_ratio()
        if ratio2 is None:
            return False

        is_black = (
            ratio1 >= config.BLACK_SCREEN_DARK_RATIO
            and ratio2 >= config.BLACK_SCREEN_DARK_RATIO
        )
        if is_black:
            self.black_screen_consecutive_hits += 1
            logger.warning(
                "⚠️ Black-screen detected "
                f"(dark_ratio={max(ratio1, ratio2):.3f}, hits={self.black_screen_consecutive_hits})"
            )
        else:
            self.black_screen_consecutive_hits = 0
        return is_black

    async def _save_black_screen_evidence(self, diag: Dict[str, Any]):
        """Persist screenshot, HTML and diagnostics for black screen analysis."""
        if not self.page:
            return
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        log_dir = Path(config.LOG_FILE).parent
        screenshot_path = log_dir / f"blackscreen_{ts}.png"
        html_path = log_dir / f"blackscreen_{ts}.html"
        json_path = log_dir / f"blackscreen_{ts}.json"
        try:
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            html = await self.page.content()
            html_path.write_text(html, encoding='utf-8')
            json_path.write_text(json.dumps(diag, ensure_ascii=False, indent=2), encoding='utf-8')
            logger.warning(f"Saved black-screen evidence: {screenshot_path.name}, {html_path.name}, {json_path.name}")
        except Exception as e:
            logger.error(f"Could not save black-screen evidence: {e}")

    async def _accept_cookie_bar_if_present(self):
        """Dismiss cookie consent bar that can interfere with interaction."""
        if not self.page:
            return
        selectors = [
            '[data-test="acceptCookieButton"]',
            'button:has-text("Acepto")',
            'button:has-text("Aceptar")',
            '.cookie-bar__button',
        ]
        for selector in selectors:
            try:
                btn = await self.page.query_selector(selector)
                if btn:
                    await btn.click()
                    logger.info("✅ Cookie banner accepted")
                    return
            except Exception:
                continue

    async def recover_from_black_screen(self) -> bool:
        """Progressive recovery for black-screen situations."""
        if not self.page:
            return False

        lobby_url = f"{config.CASINO_URL.rstrip('/')}/es/live-casino"
        for cycle in range(1, config.BLACK_SCREEN_RETRY_LIMIT + 1):
            logger.warning(f"⚠️ Starting black-screen recovery cycle {cycle}/{config.BLACK_SCREEN_RETRY_LIMIT}")
            try:
                iframe = await self._find_game_iframe_element()
                if iframe:
                    box = await iframe.bounding_box()
                    if box and box.get("width", 0) > 0 and box.get("height", 0) > 0:
                        await self.page.mouse.click(box["x"] + (box["width"] / 2), box["y"] + (box["height"] / 2))
                await asyncio.sleep(5)
                await self.inspect_game_render_state()
                if not await self.is_game_black_screen():
                    logger.info("BLACK_SCREEN_RECOVERED: click-unblock")
                    return True

                await self.page.reload(wait_until='domcontentloaded')
                await asyncio.sleep(10)
                await self._accept_cookie_bar_if_present()
                await self.inspect_game_render_state()
                if not await self.is_game_black_screen():
                    logger.info("BLACK_SCREEN_RECOVERED: page-reload")
                    return True

                await self.page.goto(lobby_url, wait_until='domcontentloaded', timeout=60000)
                await asyncio.sleep(2)
                await self.page.goto(config.GAME_URL, wait_until='domcontentloaded', timeout=60000)
                await asyncio.sleep(config.GAME_RENDER_WAIT_SECONDS)
                await self._accept_cookie_bar_if_present()
                await self.inspect_game_render_state()
                if not await self.is_game_black_screen():
                    logger.info("BLACK_SCREEN_RECOVERED: lobby-roundtrip")
                    return True
            except Exception as e:
                logger.warning(f"Black-screen recovery cycle {cycle} failed: {e}")

        return False

    async def login(self):
        """Login to casino"""
        logger.info("🔐 Attempting login...")

        if not config.CASINO_USERNAME or not config.CASINO_PASSWORD:
            logger.warning("⚠️ No credentials provided - manual login required")
            logger.info("Please login manually in the browser window...")
            await asyncio.sleep(30)  # Wait for manual login
            return

        try:
            await self._ensure_page_available()
            # Navigate to casino
            logger.info(f"🌐 Navigating to casino: {config.CASINO_URL}")
            await self.page.goto(config.CASINO_URL, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(2)
            logger.info("✅ Casino page loaded")

            # Check if already logged in
            current_url = self.page.url
            logger.info(f"Current URL: {current_url}")
            if 'casino' in current_url.lower() or 'game' in current_url.lower():
                logger.info("✅ Already logged in, skipping login")
                return

            # Look for login button/link
            login_selectors = [
                'text=Iniciar sesión',
                'text=Login',
                'text=Acceder',
                '[data-testid="login"]',
                '.login-button',
                '#login'
            ]

            login_found = False
            for selector in login_selectors:
                try:
                    login_btn = await self.page.wait_for_selector(selector, timeout=3000)
                    if login_btn:
                        logger.info(f"Found login button: {selector}")
                        await login_btn.click()
                        await asyncio.sleep(1)
                        login_found = True
                        break
                except Exception:
                    continue

            if not login_found:
                logger.warning("⚠️ No login button found, may already be logged in")

            # Fill credentials
            username_selectors = [
                'input[type="email"]', 'input[name="username"]',
                'input[name="email"]', '#username', '#email',
            ]
            password_selectors = ['input[type="password"]', 'input[name="password"]', '#password']

            username_filled = False
            for selector in username_selectors:
                try:
                    await self.page.fill(selector, config.CASINO_USERNAME, timeout=2000)
                    logger.info(f"Filled username with selector: {selector}")
                    username_filled = True
                    break
                except Exception:
                    continue

            if not username_filled:
                logger.warning("⚠️ Could not fill username field")

            password_filled = False
            for selector in password_selectors:
                try:
                    await self.page.fill(selector, config.CASINO_PASSWORD, timeout=2000)
                    logger.info(f"Filled password with selector: {selector}")
                    password_filled = True
                    break
                except Exception:
                    continue

            if not password_filled:
                logger.warning("⚠️ Could not fill password field")

            # Click submit
            submit_selectors = [
                'button[type="submit"]', 'text=Entrar',
                'text=Login', '.submit-button',
            ]
            submit_clicked = False
            for selector in submit_selectors:
                try:
                    await self.page.click(selector, timeout=2000)
                    logger.info(f"Clicked submit with selector: {selector}")
                    submit_clicked = True
                    break
                except Exception:
                    continue

            if not submit_clicked:
                logger.warning("⚠️ Could not click submit button")

            await asyncio.sleep(5)
            logger.info("✅ Login attempted")

            # Check if login was successful
            current_url_after = self.page.url
            logger.info(f"URL after login attempt: {current_url_after}")
            if 'casino' in current_url_after.lower() or 'game' in current_url_after.lower():
                logger.info("✅ Login successful")
            else:
                logger.warning("⚠️ Login may have failed - still on login page")

            # Save storage state for future sessions
            storage_state_path = Path(config.STORAGE_STATE_PATH)
            await self.context.storage_state(path=str(storage_state_path))
            logger.info(f"✅ Storage state saved to {storage_state_path}")

        except Exception as e:
            logger.error(f"Login error: {e}")
            logger.info("Please login manually...")

    async def navigate_to_game(self):
        """Navigate to the baccarat game"""
        logger.info(f"🎮 Navigating to game: {config.GAME_URL}")

        try:
            await self._ensure_page_available()
            await self.page.goto(config.GAME_URL, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(config.GAME_RENDER_WAIT_SECONDS)
            await self._accept_cookie_bar_if_present()
            logger.info("✅ Game URL loaded")
            await self.inspect_game_render_state()

            # Wait for game iframe or canvas
            game_selectors = ['iframe', 'canvas', '.game-container', '#game']

            game_found = False
            for selector in game_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=10000)
                    logger.info(f"✅ Game element found: {selector}")
                    game_found = True
                    break
                except Exception as e:
                    logger.debug(f"Game selector {selector} not found: {e}")

            if not game_found:
                logger.warning("⚠️ No game elements found - attempting login...")
                # Try login if game not found
                try:
                    await self.login()
                except Exception as e:
                    logger.error(f"Login failed: {e}")
                    logger.info("🔐 Please login manually in the browser window...")
                    logger.info("The scraper will wait 60 seconds for manual login...")
                    await asyncio.sleep(60)  # Wait for manual login
                
                # Wait a bit and check again
                await asyncio.sleep(5)
                for selector in game_selectors:
                    try:
                        await self.page.wait_for_selector(selector, timeout=10000)
                        logger.info(f"✅ Game element found after login: {selector}")
                        game_found = True
                        break
                    except Exception as e:
                        logger.debug(f"Game selector {selector} still not found: {e}")

            if not game_found:
                logger.warning("⚠️ No game elements found - game may not have loaded properly")
                # Save debug screenshot and page HTML to help diagnose black screen
                try:
                    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
                    log_dir = Path(config.LOG_FILE).parent
                    screenshot_path = log_dir / f"debug_screenshot_{ts}.png"
                    html_path = log_dir / f"debug_page_{ts}.html"
                    await self.page.screenshot(path=str(screenshot_path), full_page=True)
                    html = await self.page.content()
                    html_path.write_text(html, encoding='utf-8')
                    logger.info(f"Saved debug screenshot to {screenshot_path}")
                    logger.info(f"Saved debug page HTML to {html_path}")
                except Exception as e:
                    logger.error(f"Could not save debug screenshot/html: {e}")

            black_screen_detected = False
            if game_found and config.BLACK_SCREEN_CHECK_ENABLED:
                black_screen_detected = await self.is_game_black_screen()
                if black_screen_detected:
                    logger.warning("⚠️ Game iframe present but render appears black")
                    await self.inspect_game_render_state()
                    recovered = await self.recover_from_black_screen()
                    if not recovered:
                        diag = await self.inspect_game_render_state()
                        await self._save_black_screen_evidence(diag)
                        raise RuntimeError(
                            "Persistent black screen after recovery attempts"
                        )

            if game_found and not black_screen_detected:
                logger.info("✅ Game page navigation completed")
            elif game_found:
                logger.info("✅ Game page navigation completed after black-screen recovery")

        except Exception as e:
            logger.error(f"❌ Navigation error: {e}")
            current_url = self.page.url if self.page and not self.page.is_closed() else "N/A"
            logger.error(f"Current URL: {current_url}")
            raise

    async def run(self):
        """Main run loop"""
        try:
            await self.start()
            # Skip login for live-casino URLs as they may not require authentication
            if 'live-casino' not in config.GAME_URL:
                await self.login()
            await self.navigate_to_game()
        except Exception as e:
            logger.error(f"❌ Fatal error during startup: {e}\n{traceback.format_exc()}")
            await self.stop()
            return

        logger.info("=" * 60)
        logger.info("🎯 SCRAPER RUNNING - Waiting for results...")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 60)

        _last_status_count = 0

        try:
            while self.running:
                # Keep alive and monitor
                await asyncio.sleep(1)

                # Refresh session periodically
                if self._should_refresh_session():
                    logger.info("🔄 Refreshing session...")
                    await self._refresh_session()

                # Log status every 10 new rounds (avoid repeated logging)
                if (self.rounds_captured > 0
                        and self.rounds_captured % 10 == 0
                        and self.rounds_captured != _last_status_count):
                    _last_status_count = self.rounds_captured
                    try:
                        stats = await db.get_statistics(1)
                        logger.info(
                            f"📊 Status: {self.rounds_captured} rounds | "
                            f"Last hour: P:{stats['player_wins']} "
                            f"B:{stats['banker_wins']} T:{stats['ties']}"
                        )
                    except Exception as e:
                        logger.warning(f"Could not fetch statistics: {e}")

                # Reconnect if no frames recently
                if self._is_stale():
                    await self.inspect_game_render_state()
                    await self._reconnect_with_backoff()

        except asyncio.CancelledError:
            logger.info("Scraper cancelled")
        except KeyboardInterrupt:
            logger.info("Scraper interrupted by user")
        except Exception as e:
            logger.error(f"❌ Unexpected error in run loop: {e}\n{traceback.format_exc()}")
        finally:
            await self.stop()

    def _is_stale(self) -> bool:
        """Check if we haven't received WS frames in over 3 minutes (increased from 2)"""
        if not self.last_frame_at:
            return False
        delta = datetime.now(timezone.utc) - self.last_frame_at
        # Increased from 120s to 180s to reduce unnecessary reconnections
        stale = delta.total_seconds() > 180
        if stale:
            logger.debug(f"Stale check: last frame {delta.total_seconds():.0f}s ago")
        return stale

    def _should_refresh_session(self) -> bool:
        if not self.last_session_refresh_at:
            return True
        delta = datetime.now(timezone.utc) - self.last_session_refresh_at
        return delta.total_seconds() >= config.SESSION_REFRESH_MINUTES * 60

    async def _refresh_session(self):
        try:
            await self._ensure_page_available()
            await self.page.reload(wait_until='domcontentloaded')
            await asyncio.sleep(3)
            self.last_session_refresh_at = datetime.now(timezone.utc)
            logger.info("✅ Session refreshed")
        except Exception as e:
            logger.warning(f"Session refresh failed: {e}")

    async def _reconnect_with_backoff(self):
        active = len(self.websocket_connections)
        logger.warning(
            f"⚠️ No WS frames recently (active connections: {active})"
            f", attempting reconnect..."
        )
        await self.inspect_game_render_state()
        for attempt in range(1, config.MAX_RECONNECT_ATTEMPTS + 1):
            delay = min(5 * attempt, 30)
            logger.info(
                f"   Reconnect attempt {attempt}/"
                f"{config.MAX_RECONNECT_ATTEMPTS} (waiting {delay}s)..."
            )
            try:
                await asyncio.sleep(delay)
                await self.navigate_to_game()
                # Give the page a moment to establish WS connections
                await asyncio.sleep(5)
                self.last_frame_at = datetime.now(timezone.utc)  # Reset stale timer after navigation
                if self.websocket_connections:
                    ws_count = len(self.websocket_connections)
                    logger.info(
                        f"✅ Reconnected successfully"
                        f" ({ws_count} WS connections)"
                    )
                    return
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning(f"   Reconnect attempt {attempt} failed: {e}")
        logger.error("❌ Max reconnect attempts reached — scraper may need manual restart")

    async def stop(self):
        """Stop the scraper gracefully"""
        if not self.running and self.browser is None:
            return  # Already stopped
        logger.info("🛑 Stopping scraper...")
        self.running = False

        for resource_name, cleanup in [
            ("browser context", self._close_context),
            ("browser", self._close_browser),
            ("playwright", self._close_playwright),
            ("database", self._close_db),
        ]:
            try:
                await cleanup()
            except Exception as e:
                logger.warning(f"Error closing {resource_name}: {e}")

        logger.info(f"✅ Scraper stopped. Total rounds captured: {self.rounds_captured}")

    async def _close_context(self):
        if self.context:
            await self.context.close()
            self.context = None
            self.page = None

    async def _close_browser(self):
        if self.browser:
            await self.browser.close()
            self.browser = None

    async def _close_playwright(self):
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

    async def _close_db(self):
        await db.close()


async def main():
    """Main entry point"""
    scraper = EvolutionScraper()

    # Handle shutdown signals gracefully
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: _request_shutdown(scraper, s))

    await scraper.run()


def _request_shutdown(scraper: EvolutionScraper, sig: signal.Signals):
    """Schedule a graceful shutdown without blocking the signal handler"""
    logger.info(f"Received signal {sig.name}, scheduling shutdown...")
    scraper.running = False


if __name__ == "__main__":
    asyncio.run(main())
