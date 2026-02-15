import asyncio
import json
from playwright.async_api import async_playwright
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def capture_evolution_traffic():
    """Capturar tráfico de Evolution Gaming automáticamente"""
    
    async with async_playwright() as p:
        # Abrir navegador con proxy a mitmproxy
        browser = await p.chromium.launch(
            proxy={"server": "http://localhost:8080"},
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            # Desactivar certificado SSL (mitmproxy lo requiere)
            ignore_https_errors=True,
        )
        
        page = await context.new_page()
        
        # Interceptar respuestas
        captured_responses = []
        
        async def handle_response(response):
            """Guardar toda respuesta de Evolution Gaming"""
            if 'evolution' in response.url.lower() or 'baccarat' in response.url.lower():
                try:
                    body = await response.json()
                    captured_responses.append({
                        'url': response.url,
                        'status': response.status,
                        'body': body,
                        'headers': dict(response.headers)
                    })
                    logger.info(f"✓ Captured: {response.url}")
                    logger.info(f"  Response: {json.dumps(body, indent=2)[:300]}")
                except:
                    pass
        
        page.on("response", handle_response)
        
        # Navegar a Dragon Slot
        logger.info("🚀 Navegando a Dragon Slot...")
        await page.goto('https://www.dragongaming.com/login', wait_until='domcontentloaded')
        
        # Aquí necesitas hacer login manualmente
        logger.info("⏳ Hacer login manual... (espera 30 segundos)")
        await asyncio.sleep(30)
        
        # Ir a baccarat
        logger.info("🎮 Navegando a Baccarat...")
        await page.goto('https://www.dragongaming.com/games', wait_until='domcontentloaded')
        await asyncio.sleep(5)
        
        # Buscar y hacer click en Baccarat
        try:
            await page.click('text=Baccarat')
            logger.info("✓ Hice click en Baccarat")
        except:
            logger.warning("No encontré botón de Baccarat, busca manualmente")
        
        # Esperar y capturar requests
        logger.info("📡 Capturando tráfico de Baccarat (30 segundos)...")
        await asyncio.sleep(30)
        
        # Guardar lo capturado
        with open('captured_responses.json', 'w') as f:
            json.dump(captured_responses, f, indent=2)
        
        logger.info(f"✓ Capturadas {len(captured_responses)} responses")
        logger.info("✓ Guardadas en captured_responses.json")
        
        # Mostrar endpoints descubiertos
        endpoints = {}
        for resp in captured_responses:
            url = resp['url']
            if url not in endpoints:
                endpoints[url] = resp
        
        print("\n" + "="*60)
        print("✓ ENDPOINTS DESCUBIERTOS:")
        print("="*60)
        for url in endpoints.keys():
            print(f"\n🔗 {url}")
            print(f"   Response keys: {list(endpoints[url]['body'].keys())}")
        print("="*60)
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(capture_evolution_traffic())
