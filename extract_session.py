#!/usr/bin/env python3
"""
Extrae storage_state.json desde browser_data existente
"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    print("🔄 Extrayendo sesión desde browser_data...")
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./browser_data",
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
            ]
        )
        
        # Guardar el storage_state
        await context.storage_state(path='storage_state.json')
        print("✅ storage_state.json extraído exitosamente")
        
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
