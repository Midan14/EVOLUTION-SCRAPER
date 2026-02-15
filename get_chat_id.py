# get_chat_id.py
import asyncio
from telegram import Bot

async def get_chat_id():
    TOKEN = "TU_TOKEN_AQUI"  # Pega el token del BotFather
    bot = Bot(token=TOKEN)
    
    print("📱 Envía un mensaje a tu bot en Telegram (cualquier mensaje)")
    print("Esperando...")
    
    updates = await bot.get_updates()
    
    if updates:
        for update in updates:
            print(f"\n✅ Chat ID encontrado: {update.message.chat_id}")
            print(f"Usuario: {update.message.from_user.first_name}")
    else:
        print("❌ No hay mensajes. Envía un mensaje a tu bot primero.")

asyncio.run(get_chat_id())
