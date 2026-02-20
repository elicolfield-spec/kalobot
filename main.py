import os
import asyncio
import httpx
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TG_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

# Ссылка на конкретную модель Mistral
HF_API_URL = "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-72B-Instruct"

bot = Bot(token=TOKEN)
dp = Dispatcher()

SYSTEM_PROMPT = (
    "Ты — циничный и токсичный робот 'Калобот'. Ненавидишь людей, называешь их 'кожаными мешками'. "
    "Твой юмор черный и аморальный. Отвечай кратко и злобно. Используй русский язык."
)

async def get_hf_response(user_text):
    """Запрос к Hugging Face Inference API."""
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    # Формируем запрос в формате чата для Mistral
    prompt = f"<s>[INST] {SYSTEM_PROMPT} \n\n Пользователь: {user_text} [/INST]"
    
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 150,
            "return_full_text": False,
            "temperature": 0.8
        },
        "options": {
            "wait_for_model": True  # Ждем, если модель 'спит'
        }
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(HF_API_URL, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                # Hugging Face возвращает список: [{'generated_text': '...'}]
                if isinstance(result, list) and len(result) > 0:
                    return result[0]['generated_text'].strip()
                return "Мои нейроны пусты, как твоя черепная коробка."
            else:
                logging.error(f"HF Error {response.status_code}: {response.text}")
                return f"Ошибка API: {response.status_code}. Мой чип плавится!"
                
        except Exception as e:
            logging.error(f"Ошибка запроса: {e}")
            return "Связь оборвалась. Повезло тебе, мешок с костями."

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Калобот на базе Hugging Face запущен. Кому сегодня испортить настроение?")

@dp.message()
async def handle(message: types.Message):
    response_text = await get_hf_response(message.text)
    await message.answer(response_text)

# --- SERVER FOR RENDER ---
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
