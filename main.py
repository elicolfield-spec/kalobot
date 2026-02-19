import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from google import genai
from aiohttp import web

logging.basicConfig(level=logging.INFO)

# Токены
TG_TOKEN = os.getenv("TG_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

bot = Bot(token=TG_TOKEN)
dp = Dispatcher()
client = genai.Client(api_key=GOOGLE_API_KEY)

# --- СИСТЕМА ПАМЯТИ ---
# Храним историю в виде: {user_id: [список сообщений]}
user_history = {}

def get_history(user_id):
    if user_id not in user_history:
        user_history[user_id] = []
    return user_history[user_id]

def add_to_history(user_id, role, text):
    history = get_history(user_id)
    history.append({"role": role, "content": text})
    # Храним только последние 20 сообщений, чтобы не перегружать память
    if len(history) > 20:
        user_history[user_id] = history[-20:]
# -----------------------

async def handle(request):
    return web.Response(text="Bot is alive with memory!")

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
    user_id = message.from_user.id
    user_history[user_id] = [] # Сброс памяти при команде /start
    await message.answer("Привет! Я тебя запомнил. О чем пообщаемся?")

@dp.message()
async def chat(message: types.Message):
    if not message.text: return
    
    user_id = message.from_user.id
    history = get_history(user_id)
    
    # Добавляем сообщение пользователя в его историю
    # Для Google SDK формат может чуть отличаться, адаптируем под текст:
    prompt = ""
    for entry in history:
        prompt += f"{entry['role']}: {entry['content']}\n"
    prompt += f"user: {message.text}"

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        answer = response.text
        
        # Сохраняем диалог
        add_to_history(user_id, "user", message.text)
        add_to_history(user_id, "model", answer)
        
        await message.answer(answer)
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer("Произошла ошибка. Попробуй еще раз.")

async def main():
    await start_webserver()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
