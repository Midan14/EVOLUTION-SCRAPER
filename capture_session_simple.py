"""
Script simple para capturar sesión - espera 60 segundos para que hagas login.
"""
import asyncio
import os
from playwright.async_api import async_playwright

TARGET_URL = "https://dragonslots-1.com/es/live-casino/game/evolution/xxxtremelightningbaccarat"
STORAGE_STATE_PATH = "storage_state.json"
BROWSER_DATA_DIR = "./browser_data"

CHROMIUM_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-blink-features=AutomationControlled",
]

async def main():
    os.makedirs(BROWSER_DATA_DIR, exist_ok=True)
    
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=BROWSER_DATA_DIR,
            headless=False,
            args=CHROMIUM_ARGS,
            viewport={"width": 1920, "height": 1080},
        )

        page = context.pages[0] if context.pages else await context.new_page()
        page.set_default_navigation_timeout(120000)
        page.set_default_timeout(120000)

        print(f"🚀 Abriendo {TARGET_URL}")
        print("⏳ Esperando 90 segundos para que hagas login manual...")
        print("   (El navegador se cerrará automáticamente después)")
        
        try:
            await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=120000)
        except Exception as e:
            print(f"⚠️ Error al cargar: {e}")

        # Esperar 90 segundos para login manual
        await asyncio.sleep(90)

        # Guardar sesión
        await context.storage_state(path=STORAGE_STATE_PATH)
        print(f"✅ Sesión guardada en: {STORAGE_STATE_PATH}")

        await context.close()
        print("✅ Navegador cerrado")

if __name__ == "__main__":
    asyncio.run(main())
