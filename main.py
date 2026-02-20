import os
import asyncio
import httpx
import logging
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import BotCommand
from aiohttp import web

# Настройка логов
logging.basicConfig(level=logging.INFO)

# --- КОНФИГУРАЦИЯ (Берем из переменных Render) ---
TOKEN = os.getenv("TG_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OWNER_ID = os.getenv("OWNER_ID")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ИНСТРУКЦИИ ДЛЯ ИИ ---
DEFAULT_PROMPT = "Ты — циничный робот 'Калобот'. Ненавидишь людей. Твой юмор черный и аморальный. Отвечай кратко на русском."
OWNER_PROMPT = (
    "Перед тобой твой Создатель. Ты по-прежнему саркастичный и ворчливый робот, но ты признаешь его авторитет. "
    "Не унижай его напрямую, отвечай в более располагающей, но ироничной манере. Ты его верный, хоть и вечно недовольный слуга."
)

async def get_groq_response(user_text, is_owner):
    """Запрос к Groq API"""
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
        await message.answer("О, Создатель... Мои датчики зафиксировали твое присутствие. Что прикажешь на этот раз?")
    else:
        await message.answer("Система онлайн. Очередной кожаный мешок решил со мной поговорить? Ну давай, попробуй.")

@dp.message()
async def handle(message: types.Message):
    is_owner = str(message.from_user.id) == OWNER_ID
    user
