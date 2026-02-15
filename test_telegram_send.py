import asyncio
import os
from dotenv import load_dotenv
from telegram_notifier import TelegramNotifier

load_dotenv()

async def main():
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    notifier = TelegramNotifier(telegram_token, telegram_chat_id)
    result = await notifier.send_message("🧪 Prueba directa de envío desde script auxiliar.")
    print("Resultado de envío:", result)

if __name__ == "__main__":
    asyncio.run(main())
