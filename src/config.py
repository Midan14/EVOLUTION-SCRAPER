"""
Configuration for Evolution Gaming Baccarat Scraper
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Scraper configuration"""

    # Casino
    CASINO_URL = os.getenv("CASINO_URL", "https://dragonslots-1.com")
    CASINO_USERNAME = os.getenv("CASINO_USERNAME", "")
    CASINO_PASSWORD = os.getenv("CASINO_PASSWORD", "")

    # Game
    GAME_URL = os.getenv(
        "GAME_URL",
        "https://dragonslots-1.com/es/live-casino/game/evolution/xxxtremelightningbaccarat"
    )
    GAME_TABLE_ID = os.getenv("GAME_TABLE_ID", "xxxtremelightningbaccarat")

    # Browser
    HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
    SLOW_MO = int(os.getenv("SLOW_MO", "100"))
    VIEWPORT_WIDTH = int(os.getenv("VIEWPORT_WIDTH", "1920"))
    VIEWPORT_HEIGHT = int(os.getenv("VIEWPORT_HEIGHT", "1080"))
    BROWSER_CHANNEL = os.getenv("BROWSER_CHANNEL", "").strip()
    BROWSER_DATA_DIR = str(
        (BASE_DIR / os.getenv("BROWSER_DATA_DIR", "browser_data")).resolve()
    )
    BLACK_SCREEN_CHECK_ENABLED = (
        os.getenv("BLACK_SCREEN_CHECK_ENABLED", "false").lower() == "true"
    )
    BLACK_SCREEN_DARK_RATIO = float(os.getenv("BLACK_SCREEN_DARK_RATIO", "0.95"))
    BLACK_SCREEN_RETRY_LIMIT = int(os.getenv("BLACK_SCREEN_RETRY_LIMIT", "2"))
    GAME_RENDER_WAIT_SECONDS = int(os.getenv("GAME_RENDER_WAIT_SECONDS", "12"))
    RENDER_DIAG_ENABLED = os.getenv("RENDER_DIAG_ENABLED", "false").lower() == "true"

    # Database
    DATABASE_PATH = BASE_DIR / os.getenv("DATABASE_PATH", "data/results.db")

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = BASE_DIR / os.getenv("LOG_FILE", "logs/scraper.log")

    # API Server
    API_ENABLED = os.getenv("API_ENABLED", "true").lower() == "true"
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8899"))

    # Webhook
    WEBHOOK_ENABLED = os.getenv("WEBHOOK_ENABLED", "false").lower() == "true"
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

    # Session
    SESSION_REFRESH_MINUTES = int(os.getenv("SESSION_REFRESH_MINUTES", "30"))
    MAX_RECONNECT_ATTEMPTS = int(os.getenv("MAX_RECONNECT_ATTEMPTS", "5"))
    STORAGE_STATE_PATH = BASE_DIR / os.getenv("STORAGE_STATE_PATH", "storage_state.json")

    # Anti-Detection
    USER_AGENT = os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # Evolution Gaming specific patterns
    EVOLUTION_WS_PATTERNS = [
        "**/evolution*",
        "**/evo-*",
        "**/game/*/socket",
        "wss://*.evolution.com/*",
        "wss://*.evo*.com/*",
    ]

    EVOLUTION_XHR_PATTERNS = [
        "**/api/game/**",
        "**/api/round/**",
        "**/api/result/**",
    ]


# Lightning Baccarat Fee
LIGHTNING_FEE = float(os.getenv("LIGHTNING_FEE", "0.50"))
BANKER_COMMISSION = float(os.getenv("BANKER_COMMISSION", "0.05"))

# Bankroll Management
INITIAL_BANKROLL = float(os.getenv("INITIAL_BANKROLL", "1000"))
KELLY_FRACTION = float(os.getenv("KELLY_FRACTION", "0.25"))
MIN_EV_TO_BET = float(os.getenv("MIN_EV_TO_BET", "0.02"))

# Lightning Tracker
MULTIPLIER_HISTORY_SIZE = int(os.getenv("MULTIPLIER_HISTORY_SIZE", "50"))


config = Config()
