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

# Проверка ключа перед запуском, чтобы не было ValueError
if not GOOGLE_API_KEY:
    raise ValueError("ОШИБКА: Переменная GOOGLE_API_KEY не найдена в настройках Render!")

bot = Bot(token=TG_TOKEN)
dp = Dispatcher()
client = genai.Client(api_key=GOOGLE_API_KEY)

# Хранилище памяти: {user_id: [список сообщений]}
user_history = {}

async def handle(request):
    return web.Response(text="Bot is active!")

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
    user_history[message.from_user.id] = []
    await message.answer("Привет! Я — ИИ с памятью. Я буду помнить наш диалог, пока меня не перезагрузят.")

@dp.message()
async def chat(message: types.Message):
    if not message.text: return
    
    user_id = message.from_user.id
    
    # Получаем или создаем историю
    if user_id not in user_history:
        user_history[user_id] = []
    
    # Ограничиваем историю 10 последними фразами, чтобы сообщение не было слишком длинным
    context = "\n".join(user_history[user_id][-10:])
    full_prompt = f"{context}\nUser: {message.text}\nAI:"

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=full_prompt
        )
        answer = response.text
        
        # Сохраняем в память только короткие выжимки
        user_history[user_id].append(f"User: {message.text}")
        user_history[user_id].append(f"AI: {answer}")
        
        # Если ответ слишком длинный для Telegram, обрезаем его (на всякий случай)
        if len(answer) > 4000:
            answer = answer[:4000] + "..."
            
        await message.answer(answer)
        
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer("Упс, возникла ошибка. Попробуй сократить вопрос.")

async def main():
    await start_webserver()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
