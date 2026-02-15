#!/usr/bin/env python3
"""
DragonSlots API Scraper
Extrae datos usando HTTP requests directos (sin navegador)

Más eficiente que Playwright ya que no requiere cargar un navegador completo.
"""
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from config import config

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(config.LOG_FILE, mode='a')
    ]
)
logger = logging.getLogger(__name__)


class DragonSlotsAPI:
    """
    Cliente API para DragonSlots/Platform

    Endpoints disponibles:
    - /api/user/login - Autenticación
    - /api/user/is-auth - Verificar sesión
    - /api/v2/user-activity - Actividad del usuario
    """

    BASE_URL = "https://platform.dragonslots-1.com"
    ORIGIN = "https://dragonslots-1.com"

    def __init__(self):
        self.session: Optional[httpx.AsyncClient] = None
        self.token: Optional[str] = None
        self.user_data: Optional[Dict] = None
        self.is_authenticated = False

    def _get_headers(self, with_auth: bool = True) -> Dict[str, str]:
        """Genera headers para las peticiones"""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": self.ORIGIN,
            "Referer": f"{self.ORIGIN}/",
            "User-Agent": config.USER_AGENT,
            "client-timezone": "America/Bogota",
            "X-Requested-With": "XMLHttpRequest",
            "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
        }

        if with_auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        return headers

    async def start(self):
        """Iniciar sesión HTTP"""
        self.session = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
        )
        logger.info("✅ HTTP Client iniciado")

    async def close(self):
        """Cerrar sesión HTTP"""
        if self.session:
            await self.session.aclose()
        logger.info("🛑 HTTP Client cerrado")

    async def login(self, email: str, password: str) -> bool:
        """
        Autenticar con el casino

        Returns:
            bool: True si el login fue exitoso
        """
        logger.info(f"🔐 Intentando login con: {email}")

        try:
            # Endpoint de login
            login_url = f"{self.BASE_URL}/api/user/login"

            payload = {
                "login": email,
                "password": password,
                "remember": True
            }

            response = await self.session.post(
                login_url,
                json=payload,
                headers=self._get_headers(with_auth=False)
            )

            data = response.json()
            logger.debug(f"Login response: {json.dumps(data, indent=2)}")

            if data.get("status") == "ok" and data.get("code") == 200:
                # Extraer token del response
                if "data" in data:
                    self.token = data["data"].get("token")
                    self.user_data = data["data"].get("user", {})

                if self.token:
                    self.is_authenticated = True
                    logger.info(f"✅ Login exitoso! User ID: {self.user_data.get('id', 'N/A')}")
                    logger.info(f"   Balance: {self.user_data.get('balance', 'N/A')}")
                    return True
                else:
                    logger.error("❌ Token no encontrado en respuesta")

            else:
                error_msg = data.get("data", {}).get("messages", [])
                logger.error(f"❌ Login fallido: {error_msg or data}")

            return False

        except Exception as e:
            logger.error(f"❌ Error en login: {e}")
            return False

    async def check_auth(self) -> bool:
        """Verificar si la sesión está activa"""
        try:
            response = await self.session.get(
                f"{self.BASE_URL}/api/user/is-auth?_trlang=es",
                headers=self._get_headers()
            )

            data = response.json()
            is_auth = data.get("data", {}).get("isAuth", False)

            if is_auth:
                logger.info("✅ Sesión activa")
            else:
                logger.warning("⚠️ Sesión no activa")
                self.is_authenticated = False

            return is_auth

        except Exception as e:
            logger.error(f"Error verificando auth: {e}")
            return False

    async def get_user_activity(self) -> Optional[Dict]:
        """
        Obtener actividad del usuario

        Este endpoint puede contener historial de juegos/apuestas
        """
        try:
            response = await self.session.get(
                f"{self.BASE_URL}/api/v2/user-activity?_trlang=es",
                headers=self._get_headers()
            )

            data = response.json()

            if data.get("status") == "ok":
                logger.info("✅ Actividad obtenida")
                return data.get("data", {})
            else:
                logger.warning(f"⚠️ Error obteniendo actividad: {data}")

            return None

        except Exception as e:
            logger.error(f"Error obteniendo actividad: {e}")
            return None

    async def get_user_profile(self) -> Optional[Dict]:
        """Obtener perfil del usuario"""
        try:
            response = await self.session.get(
                f"{self.BASE_URL}/api/user/profile?_trlang=es",
                headers=self._get_headers()
            )

            return response.json() if response.status_code == 200 else None

        except Exception as e:
            logger.error(f"Error obteniendo perfil: {e}")
            return None

    async def get_game_history(
        self, game_type: str = "baccarat", limit: int = 100,
    ) -> Optional[Dict]:
        """
        Intentar obtener historial de juegos

        Nota: El endpoint exacto puede variar, esto es una aproximación
        """
        endpoints_to_try = [
            f"/api/v2/game-history?type={game_type}&limit={limit}",
            f"/api/user/game-history?limit={limit}",
            f"/api/v2/transactions?type=game&limit={limit}",
            f"/api/user/bets?limit={limit}",
        ]

        for endpoint in endpoints_to_try:
            try:
                response = await self.session.get(
                    f"{self.BASE_URL}{endpoint}&_trlang=es",
                    headers=self._get_headers()
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "ok":
                        logger.info(f"✅ Historial encontrado en: {endpoint}")
                        return data

            except Exception as e:
                logger.debug(f"Endpoint {endpoint} no disponible: {e}")

        return None

    async def discover_endpoints(self) -> Dict[str, Any]:
        """
        Descubrir endpoints disponibles

        Prueba varios endpoints comunes para ver cuáles responden
        """
        logger.info("🔍 Descubriendo endpoints disponibles...")

        endpoints = [
            "/api/user/profile",
            "/api/user/balance",
            "/api/user/notifications",
            "/api/v2/user-activity",
            "/api/v2/games",
            "/api/v2/casino/games",
            "/api/v2/casino/providers",
            "/api/v2/transactions",
            "/api/v2/game-history",
            "/api/user/game-history",
            "/api/user/bets",
            "/api/casino/live",
            "/api/evolution/tables",
        ]

        available = {}

        for endpoint in endpoints:
            try:
                response = await self.session.get(
                    f"{self.BASE_URL}{endpoint}?_trlang=es",
                    headers=self._get_headers()
                )

                status = response.status_code

                if status == 200:
                    data = response.json()
                    available[endpoint] = {
                        "status": "OK",
                        "response_preview": str(data)[:200]
                    }
                    logger.info(f"  ✅ {endpoint} - OK")
                elif status == 401:
                    logger.debug(f"  ⚠️ {endpoint} - Auth required")
                elif status == 404:
                    logger.debug(f"  ❌ {endpoint} - Not found")
                else:
                    logger.debug(f"  ⚠️ {endpoint} - Status {status}")

            except Exception as e:
                logger.debug(f"  ❌ {endpoint} - Error: {e}")

        return available


async def main():
    """Test del API client"""
    api = DragonSlotsAPI()

    try:
        await api.start()

        # Login
        email = config.CASINO_USERNAME
        password = config.CASINO_PASSWORD

        if not email or not password:
            logger.error("❌ Credenciales no configuradas en .env")
            return

        success = await api.login(email, password)

        if not success:
            logger.error("❌ No se pudo autenticar")
            return

        # Verificar auth
        await api.check_auth()

        # Descubrir endpoints
        print("\n" + "=" * 60)
        print("🔍 ENDPOINTS DISPONIBLES")
        print("=" * 60)

        endpoints = await api.discover_endpoints()

        for endpoint, info in endpoints.items():
            print(f"\n📍 {endpoint}")
            print(f"   Preview: {info['response_preview'][:100]}...")

        # Obtener actividad
        print("\n" + "=" * 60)
        print("📊 USER ACTIVITY")
        print("=" * 60)

        activity = await api.get_user_activity()
        if activity:
            print(json.dumps(activity, indent=2, ensure_ascii=False))

    finally:
        await api.close()


if __name__ == "__main__":
    asyncio.run(main())
