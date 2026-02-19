import os
import logging
import asyncio
import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from google import genai
from google.genai import types as genai_types

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация токенов из переменных окружения
TG_TOKEN = os.getenv("TG_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Инициализация ботов и клиентов
bot = Bot(token=TG_TOKEN)
dp = Dispatcher()
google_client = genai.Client(api_key=GOOGLE_API_KEY)

# Хранилище контекста (память на 6 сообщений)
user_history = {}

async def get_ai_response(user_id, text):
    # Собираем контекст
    history = user_history.get(user_id, [])
    context = "\n".join(history[-6:])
    full_prompt = f"{context}\nUser: {text}\nAI:"

    # --- План А: Прямой Google AI ---
    try:
        logger.info(f"Попытка Google AI для {user_id}")
        response = google_client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=full_prompt
        )
        if response.text:
            return response.text
    except Exception as e:
        logger.warning(f"Google AI отказал (лимит/регион). Переходим к OpenRouter...")

    # --- План Б: Перебор моделей в OpenRouter ---
    models_to_try = [
        "google/gemini-2.0-flash-exp:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "deepseek/deepseek-chat:free"
    ]

    if OPENROUTER_API_KEY:
        async with httpx.AsyncClient(timeout=60.0) as client:
            for model_name in models_to_try:
                try:
                    logger.info(f"Пробую модель {model_name} через OpenRouter...")
                    resp = await client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                            "HTTP-Referer": "https://render.com",
                            "X-Title": "Kalobot"
                        },
                        json={
                            "model": model_name,
                            "messages": [{"role": "user", "content": full_prompt}]
                        }
                    )
                    
                    if resp.status_code == 200:
                        result = resp.json()
                        if 'choices' in result and len(result['choices']) > 0:
                            return result['choices'][0]['message']['content']
                    
                    logger.error(f"Модель {model_name} вернула статус {resp.status_code}")
                    await asyncio.sleep(1) # Короткая пауза перед следующей попыткой
                except Exception as e:
                    logger.error(f"Ошибка при обращении к {model_name}: {e}")
                    continue

    return "Извини, все мои нейронные связи сейчас заняты (ошибка лимитов). Попробуй написать чуть позже!"

@dp.message(Command("start"))
async def start_command(message: types.Message):
    user_history[message.from_user.id] = []
    await message.answer("Привет! Я твой ИИ-бот. Я готов общаться, даже если основные лимиты Google на пределе. Что обсудим?")

@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    user_text = message.text

    # Отправляем статус "печатает"
    await bot.send_chat_action(message.chat.id, "typing")

    # Получаем ответ от ИИ
    response_text = await get_ai_response(user_id, user_text)

    # Обновляем историю (для памяти)
    if user_id not in user_history:
        user_history[user_id] = []
    user_history[user_id].append(f"User: {user_text}")
    user_history[user_id].append(f"AI: {response_text}")

    # Отвечаем пользователю
    await message.answer(response_text)

async def main():
    logger.info("Бот запущен и готов к работе...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
