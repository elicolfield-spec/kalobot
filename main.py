import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from google import genai
from aiohttp import web

# Логи
logging.basicConfig(level=logging.INFO)

# Токены
TG_TOKEN = os.getenv("TG_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

bot = Bot(token=TG_TOKEN)
dp = Dispatcher()
# Инициализация клиента Google
client = genai.Client(api_key=GOOGLE_API_KEY)

# Веб-сервер для Render (чтобы не спал)
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_webserver():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("Привет! Теперь я работаю на прямом канале Google AI. Спрашивай что угодно!")

@dp.message()
async def chat(message: types.Message):
    if not message.text: return
    
    try:
        # Запрос к Gemini 2.0 Flash (самая быстрая бесплатная модель)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=message.text
        )
        await message.answer(response.text)
    except Exception as e:
        logging.error(f"Ошибка Google AI: {e}")
        await message.answer("Произошла ошибка при обращении к Google. Попробуй позже.")

async def main():
    await start_webserver()
    logging.info("Бот запущен через Google AI Studio")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
