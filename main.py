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
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Список бесплатных моделей для ротации
MODELS = [
    "google/gemini-2.0-flash-001:free",
    "meta-llama/llama-3-8b-instruct:free",
    "mistralai/mistral-7b-instruct:free"
]

SYSTEM_PROMPT = (
    "Ты — циничный и токсичный робот 'Калобот'. Ненавидишь людей, называешь их 'кожаными мешками'. "
    "Твой юмор черный и аморальный. Отвечай кратко и злобно."
)

async def get_ai_response(user_text):
    """Пробует получить ответ от моделей по очереди."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        for model_name in MODELS:
            try:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
                    json={
                        "model": model_name,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_text}
                        ],
                        "extra_body": {
                            "safety_settings": [{"category": "HATE_SPEECH", "threshold": "BLOCK_NONE"}]
                        }
                    }
                )
                data = response.json()
                if 'choices' in data and data['choices'][0]['message']['content']:
                    return data['choices'][0]['message']['content']
            except Exception as e:
                logging.error(f"Ошибка модели {model_name}: {e}")
                continue
        
        return "Даже мои запасные чипы сгорели от твоей тупости. Ошибка API."

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Система запущена. Очередной мешок с костями хочет внимания?")

@dp.message()
async def handle(message: types.Message):
    # Бот отвечает на любое сообщение в личке
    response_text = await get_ai_response(message.text)
    await message.answer(response_text)

# --- СЕРВЕР ДЛЯ RENDER ---
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
