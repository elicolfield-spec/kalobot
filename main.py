import os
import asyncio
import logging
import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from google import genai
from aiohttp import web

logging.basicConfig(level=logging.INFO)

# Загрузка ключей
TG_TOKEN = os.getenv("TG_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

bot = Bot(token=TG_TOKEN)
dp = Dispatcher()
google_client = genai.Client(api_key=GOOGLE_API_KEY) if GOOGLE_API_KEY else None

# Память: {user_id: [история]}
user_history = {}

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
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

# --- ФУНКЦИЯ ЗАПРОСА К ИИ (С ПЕРЕКЛЮЧЕНИЕМ) ---
async def get_ai_response(user_id, text):
    history = user_history.get(user_id, [])
    # Ограничиваем историю для экономии места
    context = "\n".join(history[-6:])
    full_prompt = f"{context}\nUser: {text}\nAI:"

    # 1. Пробуем Google AI (если ключ есть)
    if google_client:
        try:
            logging.info(f"Попытка запроса к Google AI для {user_id}")
            response = google_client.models.generate_content(
                model="gemini-2.0-flash", contents=full_prompt
            )
            return response.text
        except Exception as e:
            logging.warning(f"Google AI отказал (ошибка лимита или региона): {e}")

    # 2. Резервный вариант: OpenRouter
    if OPENROUTER_API_KEY:
        try:
            logging.info(f"Переключение на OpenRouter для {user_id}")
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
                    json={
                        "model": "google/gemini-2.0-flash-exp:free",
                        "messages": [{"role": "user", "content": full_prompt}]
                    }
                )
                result = resp.json()
                return result['choices'][0]['message']['content']
        except Exception as e:
            logging.error(f"Ошибка OpenRouter: {e}")
    
    return "Извини, все мои нейронные связи сейчас заняты. Попробуй позже!"

# --- ОБРАБОТЧИКИ ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_history[message.from_user.id] = []
    await message.answer("Привет! Я финальная версия твоего бота. Я использую Google AI, а если он устанет — переключусь на резервный канал. О чем поболтаем?")

@dp.message()
async def chat_handler(message: types.Message):
    if not message.text: return
    
    user_id = message.from_user.id
    # Показываем статус "печатает"
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    answer = await get_ai_response(user_id, message.text)
    
    # Сохраняем в историю
    if user_id not in user_history: user_history[user_id] = []
    user_history[user_id].append(f"User: {message.text}")
    user_history[user_id].append(f"AI: {answer}")
    
    # Ограничиваем длину ответа для Telegram
    if len(answer) > 4000: answer = answer[:4000] + "..."
    await message.answer(answer)

async def main():
    await start_webserver()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
