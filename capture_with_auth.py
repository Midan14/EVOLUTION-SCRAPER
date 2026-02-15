import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright

TARGET_URL = "https://dragonslots-1.com/es/live-casino/game/evolution/xxxtremelightningbaccarat"

async def main():
    messages = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Interceptar WebSocket
        def handle_websocket(ws):
            print(f"✅ WebSocket conectado: {ws.url}")
            
            def on_frame(payload):
                try:
                    # Solo si es texto
                    if isinstance(payload, str):
                        data = json.loads(payload)
                        
                        msg = {
                            'timestamp': datetime.now().isoformat(),
                            'data': data
                        }
                        messages.append(msg)
                        
                        print(f"\n[WS] {datetime.now().strftime('%H:%M:%S')}")
                        print(json.dumps(data, indent=2)[:600])
                        print("-"*60)
                except:
                    pass
            
            ws.on('framereceived', on_frame)
        
        page.on('websocket', handle_websocket)
        
        print(f"🚀 Abriendo {TARGET_URL}")
        await page.goto(TARGET_URL)
        
        print("\n⏳ INSTRUCCIONES:")
        print("   1. Loguéate si es necesario")
        print("   2. Entra a la mesa de baccarat")
        print("   3. Espera que se jueguen 3-5 rondas")
        print("   4. Los datos se están capturando automáticamente...")
        print("\n   Presiona Ctrl+C cuando tengas suficientes datos\n")
        
        try:
            # Esperar indefinidamente (hasta Ctrl+C)
            await asyncio.sleep(999999)
        except KeyboardInterrupt:
            print("\n⛔ Deteniendo captura...")
        
        # Guardar
        with open('ws_messages_authenticated.json', 'w') as f:
            json.dump(messages, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Capturados {len(messages)} mensajes")
        print(f"📁 Guardado en: ws_messages_authenticated.json")
        
        # Resumen
        if messages:
            types = {}
            for msg in messages:
                t = msg['data'].get('type', msg['data'].get('mt', 'unknown'))
                types[t] = types.get(t, 0) + 1
            
            print("\n📊 TIPOS DE MENSAJE:")
            for t, c in sorted(types.items(), key=lambda x: x[1], reverse=True):
                print(f"   {t}: {c}")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
