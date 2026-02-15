"""
Guarda la sesión del casino (cookies, etc.) para usarla en el bot.
Usa la misma configuración que dragon_bot_ml.py para evitar cierres inesperados.
"""
import asyncio
import os
from playwright.async_api import async_playwright

TARGET_URL = os.getenv(
    "TARGET_URL",
    "https://dragonslots-1.com/es/live-casino/game/evolution/xxxtremelightningbaccarat"
)
STORAGE_STATE_PATH = os.getenv("STORAGE_STATE_PATH", "storage_state.json")
READY_FLAG_PATH = os.getenv("STORAGE_STATE_READY", "storage_state.ready")
BROWSER_DATA_DIR = os.getenv("BROWSER_DATA_DIR", "./browser_data")

# Mismos args y configuración que dragon_bot_ml.py para estabilidad
CHROMIUM_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-blink-features=AutomationControlled",
]
VIEWPORT = {"width": 1920, "height": 1080}
NAV_TIMEOUT = 120000


async def main():
    os.makedirs(BROWSER_DATA_DIR, exist_ok=True)
    # Quitar flag de una ejecución anterior para que esta vez espere a que confirmes
    if os.path.exists(READY_FLAG_PATH):
        os.remove(READY_FLAG_PATH)

    async with async_playwright() as p:
        # Mismo launch_persistent_context que el bot (sin storage_state) para no cerrarse inesperadamente
        context = await p.chromium.launch_persistent_context(
            user_data_dir=BROWSER_DATA_DIR,
            headless=False,
            args=CHROMIUM_ARGS,
            viewport=VIEWPORT,
        )

        page = context.pages[0] if context.pages else await context.new_page()
        page.set_default_navigation_timeout(NAV_TIMEOUT)
        page.set_default_timeout(NAV_TIMEOUT)

        print(f"🚀 Abriendo {TARGET_URL}")
        try:
            await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
        except Exception as e:
            print(f"⚠️ La página tardó en cargar: {e}")
            print("✅ Si el navegador se abrió, continúa el login manual igualmente.")

        print("✅ Inicia sesión manualmente y entra a la mesa.")
        print("✅ Cuando ya estés dentro, crea el archivo de confirmación:")
        print(f"   touch \"{READY_FLAG_PATH}\"")

        while not os.path.exists(READY_FLAG_PATH):
            await asyncio.sleep(2)

        await context.storage_state(path=STORAGE_STATE_PATH)
        print(f"✅ Sesión guardada en: {STORAGE_STATE_PATH}")

        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
