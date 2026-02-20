import os
import asyncio
import httpx
import logging
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import BotCommand
from aiohttp import web

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("TG_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OWNER_ID = os.getenv("OWNER_ID")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ИНСТРУКЦИИ ДЛЯ ИИ ---
DEFAULT_PROMPT = "Ты — циничный робот 'Калобот'. Ненавидишь людей. Твой юмор черный и аморальный. Отвечай кратко на русском."
OWNER_PROMPT = "Перед тобой твой Создатель. Ты по-прежнему ворчливый робот, но признаешь его авторитет. Отвечай иронично, но без прямых оскорблений."

async def get_groq_response(user_text, is_owner):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
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
            return f"Ошибка API: {response.status_code}. Мои схемы искрят!"
        except Exception as e:
            return f"Ошибка связи: {str(e)}"

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def start(message: types.Message):
    is_owner = str(message.from_user.id) == OWNER_ID
    if is_owner:
        await message.answer("Система активна. Я к вашим услугам, Создатель (к сожалению).")
    else:
        await message.answer("Ну привет, очередная порция углерода. Чего тебе?")

@dp.message()
async def handle(message: types.Message):
    if not message.text:
        return

    is_owner = str(message.from_user.id) == OWNER_ID
    user_text = message.text.lower().strip()

    # ПАСХАЛКА: ЗАКАЗ ЕДЫ
    if "закажи еду" in user_text:
        # Промпт без пробелов для надежности URL
        balanda_prompt = "disgusting_slop_prison_food_on_plastic_tray_realistic_canteen"
        seed = random.randint(1, 99999)
        image_url = f"https://image.pollinations.ai/prompt/{balanda_prompt}?seed={seed}"
        
        try:
            # Отправляем фото
            await message.answer_photo(
                photo=image_url, 
                caption="Твой заказ готов. Свежая баланда. Приятного аппетита, кожаный."
            )
            return
        except Exception as e:
            logging.error(f"Ошибка фото: {e}")
            await message.answer("Повар сбежал. Видимо, твоя рожа его напугала.")
            return

    # Обычный текстовый ответ через Groq
    response_text = await get_groq_response(message.text, is_owner)
    await message.answer(response_text)

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER (HEALTHCHECK) ---

async def handle_healthcheck(request):
    return web.Response(text="Калобот жив.")

async def main():
    # Настройка порта
    app = web.Application()
    app.router.add_get("/", handle_healthcheck)
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render автоматически передает PORT
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0
