#!/usr/bin/env python3
"""Script de diagnóstico para detectar la página de login del casino."""
import asyncio
from playwright.async_api import async_playwright
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    casino_url = os.getenv("CASINO_URL", "https://dragonslots-1.com")
    username = os.getenv("CASINO_USERNAME")
    password = os.getenv("CASINO_PASSWORD")
    
    print(f"🔍 Analizando login en: {casino_url}")
    print(f"👤 Usuario: {username}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print(f"\n1️⃣ Abriendo página principal...")
        await page.goto(casino_url, wait_until="domcontentloaded", timeout=120000)
        await asyncio.sleep(3)
        
        # Buscar botón de login
        print("\n2️⃣ Buscando botones de login...")
        login_buttons = await page.locator("text=/login|iniciar|entrar|acceder|sign in/i").all()
        print(f"   Encontrados {len(login_buttons)} botones")
        
        for i, btn in enumerate(login_buttons[:5]):  # Solo primeros 5
            try:
                text = await btn.text_content()
                visible = await btn.is_visible()
                print(f"   Botón {i+1}: '{text}' (visible: {visible})")
            except:
                pass
        
        # Intentar hacer clic en el primero visible
        print("\n3️⃣ Haciendo clic en botón de login...")
        for btn in login_buttons:
            try:
                if await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(2)
                    print("   ✅ Clic exitoso")
                    break
            except Exception as e:
                print(f"   ⚠️ Error al hacer clic: {e}")
        
        # Buscar inputs de login en todos los frames
        print("\n4️⃣ Buscando inputs de login...")
        for frame in page.frames:
            try:
                user_inputs = await frame.locator("input[type='email'], input[type='text'], input[name*='user' i], input[name*='email' i]").all()
                pass_inputs = await frame.locator("input[type='password']").all()
                
                if user_inputs or pass_inputs:
                    print(f"\n   Frame: {frame.url}")
                    print(f"   - Inputs de usuario: {len(user_inputs)}")
                    print(f"   - Inputs de password: {len(pass_inputs)}")
                    
                    # Mostrar detalles de los inputs
                    for i, inp in enumerate(user_inputs[:3]):
                        try:
                            name = await inp.get_attribute("name")
                            placeholder = await inp.get_attribute("placeholder")
                            visible = await inp.is_visible()
                            print(f"      User input {i+1}: name='{name}', placeholder='{placeholder}', visible={visible}")
                        except:
                            pass
                    
                    for i, inp in enumerate(pass_inputs[:3]):
                        try:
                            name = await inp.get_attribute("name")
                            placeholder = await inp.get_attribute("placeholder")
                            visible = await inp.is_visible()
                            print(f"      Pass input {i+1}: name='{name}', placeholder='{placeholder}', visible={visible}")
                        except:
                            pass
            except Exception as e:
                print(f"   ⚠️ Error en frame: {e}")
        
        # Tomar screenshot
        print("\n5️⃣ Tomando screenshot...")
        await page.screenshot(path="login_debug.png")
        print("   ✅ Screenshot guardada: login_debug.png")
        
        print("\n⏳ Esperando 60 segundos para inspección manual...")
        print("   (Puedes hacer login manualmente en el navegador)")
        await asyncio.sleep(60)
        
        await browser.close()
        print("\n✅ Diagnóstico completo")

if __name__ == "__main__":
    asyncio.run(main())
