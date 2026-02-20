import os
import asyncio
import httpx
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

logging.basicConfig(level=logging.INFO)

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("TG_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = Bot(token=TOKEN)
dp = Dispatcher()

SYSTEM_PROMPT = "Ты — циничный робот 'Калобот'. Ненавидишь людей. Твой юмор черный. Отвечай кратко на русском."

async def get_groq_response(user_text):
    """Запрос к Groq API — самому быстрому и щедрому на сегодня."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile", # Топовая и быстрая модель
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ],
        "temperature": 0.9
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content']
            else:
                logging.error(f"Groq Error: {response.status_code} - {response.text}")
                return f"Ошибка Groq: {response.status_code}. Мои шестерни заклинило."
        except Exception as e:
            return f"Ошибка связи: {str(e)}"

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Система онлайн. Чего тебе, кожаный?")

@dp.message()
async def handle(message: types.Message):
    # Бот отвечает на всё в личных сообщениях
    response_text = await get_groq_response(message.text)
    await message.answer(response_text)

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---

async def handle_healthcheck(request):
    return web.Response(text="I'm alive.")

async def main():
    app = web.Application()
    app.router.add_get("/", handle_healthcheck)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 8080)))
    await site.start()

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
