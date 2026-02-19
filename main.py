import os
import logging
import asyncio
import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация токенов
TG_TOKEN = os.getenv("TG_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Инициализация бота
bot = Bot(token=TG_TOKEN)
dp = Dispatcher()

# Память бота (последние 6 сообщений)
user_history = {}

async def get_ai_response(user_id, text):
    history = user_history.get(user_id, [])
    context = "\n".join(history[-6:])
    full_prompt = f"{context}\nUser: {text}\nAI:"

    # Список надежных бесплатных моделей
    models_to_try = [
        "google/gemini-2.0-flash-exp:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "mistralai/mistral-small-24b-instruct-2501:free"
    ]

    async with httpx.AsyncClient(timeout=60.0) as client:
        for model_name in models_to_try:
            try:
                logger.info(f"Запрос к {model_name} через OpenRouter...")
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
                
                logger.warning(f"Модель {model_name} не ответила (Статус: {resp.status_code})")
            except Exception as e:
                logger.error(f"Ошибка при обращении к {model_name}: {e}")
            
            await asyncio.sleep(0.5) # Минимальная пауза между попытками

    return "Все бесплатные каналы сейчас перегружены. Попробуй повторить через минуту!"

@dp.message(Command("start"))
async def start_command(message: types.Message):
    user_history[message.from_user.id] = []
    await message.answer("Бот перезапущен в режиме OpenRouter. Я готов к общению! О чем поговорим?")

@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    user_text = message.text

    await bot.send_chat_action(message.chat.id, "typing")
    response_text = await get_ai_response(user_id, user_text)

    # Обновление истории
    if user_id not in user_history:
        user_history[user_id] = []
    user_history[user_id].append(f"User: {user_text}")
    user_history[user_id].append(f"AI: {response_text}")

    await message.answer(response_text)

async def main():
    logger.info("Бот запущен (OpenRouter Mode)...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
