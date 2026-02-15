import asyncio
import websockets
import json
from datetime import datetime

WS_URL = "wss://sapa-mdp-e03.egcvi.com/app/30/xlb1_bi_hd/websocketstream2?vc=h264&ac=opus&videoSessionId=st4dwah4xkcbvcsk-st4dwah4xkcbvcsktqbrlwxh6hiofmxn78cbf978b1a670d8f088502c7562df43bb45b5e367e8bb47-XXXtremeLB000001-2cb4fa&videoToken=eyJhbGciOiJSUzI1NiIsImtpZCI6ImxpdmUxMDEiLCJ0eXAiOiJKV1QifQ.eyJhdWQiOiJzYXBhLW1kcC1lMDMiLCJiaWQiOiJvaGlhLXZsb2FkZXIwMiIsImNpcCI6IjE0Ni43MC4xMzYuMTQiLCJjc24iOiJhOHIwMDAwMDAwMDAwMDBxIiwiZGxoIjoiYThyLmV2by1nYW1lcy5jb20iLCJleHAiOjE3Njk1NzgzOTgsImlzcyI6IkwxeTZxcmVOTFMiLCJyb2giOiJodHRwczpcL1wvYThyLmV2by1nYW1lcy5jb20iLCJzdWIiOiJ4bGIxX2JpIiwidnNpZCI6InN0NGR3YWg0eGtjYnZjc2stc3Q0ZHdhaDR4a2NidmNza3RxYnJsd3hoNmhpb2ZteG43OGNiZjk3OGIxYTY3MGQ4ZjA4ODUwMmM3NTYyZGY0M2JiNDViNWUzNjdlOGJiNDctWFhYdHJlbWVMQjAwMDAwMS0yY2I0ZmEifQ.f3XxHaYPzKYpHLzZ-QPdep8uF2Tw6XkPwM2RUggUdkh6bJ8lwTEAPH6UYahY4ILMtulu7HUl0joGnjnl5PyINZPe3g5QNiPyS9sr7GFIoN6HRKAbZcEDD5Q_BfQmdDwD27IK0lx1xHA8pyBdx4ZbO88xrkL-gdIp4YIpgsMye0ba6BmO2VncJkdxucr3BSHyCggHDtFhyAn0u4tFB9YnJVYEP8ZH_1_q_fVYw7NBhYrcGdYRwGFf3JkSW4PC4rMrBuYuFDqneRBzc-dIxy0P_DOiSMZf1XwTE6LHFhNQR2_gRorqEfXuPSi5H3NHyd_Ihc4OU-PKF6eEZTkloJCtEg"

async def capture_messages():
    messages = []
    
    try:
        print(f"🔌 Conectando a WebSocket...")
        
        # Versión corregida para websockets 15.0+
        async with websockets.connect(
            WS_URL,
            additional_headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                "Origin": "https://dragonslots-1.com"
            }
        ) as websocket:
            print("✅ Conectado!")
            print("📡 Capturando mensajes... (Ctrl+C para detener)")
            print("="*60)
            
            counter = 0
            binary_counter = 0
            
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                    
                    # Si es texto, intentar parsear como JSON
                    if isinstance(message, str):
                        try:
                            data = json.loads(message)
                            counter += 1
                            
                            msg_data = {
                                'index': counter,
                                'timestamp': datetime.now().isoformat(),
                                'data': data
                            }
                            messages.append(msg_data)
                            
                            # Mostrar en consola
                            print(f"\n[JSON #{counter}] {datetime.now().strftime('%H:%M:%S')}")
                            print(json.dumps(data, indent=2)[:800])
                            print("-"*60)
                            
                        except json.JSONDecodeError:
                            print(f"[Text no-JSON] {message[:100]}")
                    else:
                        # Es binario (video/audio)
                        binary_counter += 1
                        if binary_counter % 100 == 0:
                            print(f"[Binary frames: {binary_counter}]")
                
                except asyncio.TimeoutError:
                    print("⏱️  Timeout (60s) - sin mensajes nuevos")
                    break
                except KeyboardInterrupt:
                    print("\n⛔ Detenido por usuario")
                    break
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Guardar todo lo capturado
        output_file = 'websocket_messages.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(messages, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Capturados {len(messages)} mensajes JSON")
        print(f"📁 Guardado en: {output_file}")
        
        # Mostrar resumen
        if messages:
            types = {}
            for msg in messages:
                if isinstance(msg.get('data'), dict):
                    msg_type = msg['data'].get('type', msg['data'].get('mt', 'unknown'))
                    types[msg_type] = types.get(msg_type, 0) + 1
            
            if types:
                print("\n📊 RESUMEN DE TIPOS DE MENSAJE:")
                for msg_type, count in sorted(types.items(), key=lambda x: x[1], reverse=True):
                    print(f"   {msg_type}: {count}")

if __name__ == "__main__":
    try:
        asyncio.run(capture_messages())
    except KeyboardInterrupt:
        print("\n⛔ Script detenido")
