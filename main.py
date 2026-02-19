import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import httpx
from aiohttp import web

# Настройка логов
logging.basicConfig(level=logging.INFO)

# Токены
TG_TOKEN = os.getenv("TG_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

bot = Bot(token=TG_TOKEN)
dp = Dispatcher()

# Мини веб-сервер для Render
async def handle(request):
    return web.Response(text="I am alive!")

async def start_webserver():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render дает порт в переменную среды PORT
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("Привет! Я твой ИИ-бот. Спрашивай что угодно!")

@dp.message()
async def chat(message: types.Message):
    if not message.text: return
    
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
    data = {
        "model": "openrouter/auto",
        "messages": [{"role": "user", "content": message.text}]
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
            result = response.json()
            answer = result['choices'][0]['message']['content']
            await message.answer(answer)
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer("ИИ призадумался. Попробуй еще раз!")

async def main():
    # Запускаем веб-сервер и бота одновременно
    await start_webserver()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
