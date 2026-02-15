#!/usr/bin/env python3
"""
Script rápido para guardar storage_state.json
Mantiene el navegador abierto para que puedas hacer login manualmente
"""
import asyncio
import os
from playwright.async_api import async_playwright

async def main():
    print("🚀 Abriendo navegador...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = await context.new_page()
        
        print("🌐 Navegando al casino...")
        await page.goto('https://dragonslots-1.com/es/live-casino/game/evolution/xxxtremelightningbaccarat')
        
        print("")
        print("=" * 60)
        print("✅ HAZ LOGIN MANUALMENTE EN EL NAVEGADOR")
        print("✅ Entra a la mesa de XXXtreme Lightning Baccarat")
        print("✅ Cuando estés dentro, presiona ENTER aquí en la terminal")
        print("=" * 60)
        print("")
        
        # Esperar input del usuario
        input("Presiona ENTER cuando hayas completado el login: ")
        
        # Guardar la sesión
        await context.storage_state(path='storage_state.json')
        print("✅ Sesión guardada en storage_state.json")
        
        await browser.close()
        print("✅ Navegador cerrado")

if __name__ == "__main__":
    asyncio.run(main())
