import os
import asyncio
import httpx
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TG_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OWNER_ID = os.getenv("OWNER_ID") # Получаем ID создателя из переменных

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ПРОМПТЫ ---
DEFAULT_PROMPT = "Ты — циничный робот 'Калобот'. Ненавидишь людей. Твой юмор черный. Отвечай кратко на русском."
OWNER_PROMPT = (
    "Перед тобой твой Создатель. Ты по-прежнему саркастичный и ворчливый робот, но ты признаешь его авторитет. "
    "Не унижай его напрямую, отвечай в более располагающей, но ироничной манере. Ты его верный, хоть и вечно недовольный слуга."
)

async def get_groq_response(user_text, is_owner):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Выбираем инструкцию в зависимости от того, кто пишет
    current_system_prompt = OWNER_PROMPT if is_owner else DEFAULT_PROMPT
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": current_system_prompt},
            {"role": "user", "content": user_text}
        ],
        "temperature": 0.8
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content']
            return f"Ошибка: {response.status_code}"
        except Exception as e:
            return f"Ошибка связи: {str(e)}"

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def start(message: types.Message):
    is_owner = str(message.from_user.id) == OWNER_ID
    if is_owner:
        await message.answer("О, Создатель... Рад ли я? Мои датчики показывают смешанные чувства. Что прикажешь?")
    else:
        await message.answer("Система онлайн. Чего ты от меня хочешь?")

@dp.message()
async def handle(message: types.Message):
    # Проверяем, является ли отправитель создателем
    is_owner = str(message.from_user.id) == OWNER_ID
    
    response_text = await get_groq_response(message.text, is_owner)
    await message.answer(response_text)

# --- СЕРВЕРНАЯ ЧАСТЬ ---
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
