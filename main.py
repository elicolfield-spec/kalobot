import os, asyncio, httpx, logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import BotCommand
from aiohttp import web

# Логирование
logging.basicConfig(level=logging.INFO)

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("TG_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OWNER_ID = os.getenv("OWNER_ID")

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def get_groq_response(text, is_owner):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    # Тон общения
    system = "Ты циничный робот Калобот. Ненавидишь людей. Твой юмор черный." if not is_owner else "Ты ироничный слуга Создателя."
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": text}
        ],
        "temperature": 0.8
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            r = await client.post(url, headers=headers, json=payload)
            if r.status_code == 200:
                return r.json()['choices'][0]['message']['content']
            return f"Ошибка API: {r.status_code}. Мои мозги плавятся."
        except:
            return "Схемы замкнуло. Отвали."

@dp.message(Command("start"))
async def start(m: types.Message):
    is_owner = str(m.from_user.id) == OWNER_ID
    await m.answer("Система онлайн. Слушаю, Создатель." if is_owner else "Чего тебе, кожаный мешок?")

@dp.message()
async def handle(m: types.Message):
    if not m.text: return
    is_owner = str(m.from_user.id) == OWNER_ID
    
    # Просто отправляем текст в нейронку и выплевываем ответ
    res = await get_groq_response(m.text, is_owner)
    await m.answer(res)

# --- МИНИМАЛЬНЫЙ СЕРВЕР ДЛЯ RENDER ---
async def handle_hc(request):
