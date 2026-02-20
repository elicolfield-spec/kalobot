import os
import asyncio
import httpx
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

# Настройка логов, чтобы видеть, какая модель ответила
logging.basicConfig(level=logging.INFO)

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("TG_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

# Список надежных моделей на Hugging Face для ротации
HF_MODELS = [
    "https://api-inference.huggingface.co/models/microsoft/Phi-3-mini-4k-instruct",
    "https://api-inference.huggingface.co/models/google/gemma-2-9b-it",
    "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"
]

bot = Bot(token=TOKEN)
dp = Dispatcher()

SYSTEM_PROMPT = (
    "Ты — циничный и токсичный робот 'Калобот'. Ненавидишь людей, называешь их 'кожаными мешками'. "
    "Твой юмор черный и аморальный. Отвечай кратко и злобно. Используй русский язык."
)

async def get_hf_response(user_text):
    """Пробует достучаться до моделей Hugging Face по очереди."""
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    # Универсальный шаблон диалога
    prompt = f"<|system|>\n{SYSTEM_PROMPT}<|end|>\n<|user|>\n{user_text}<|end|>\n<|assistant|>"
    
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 150, 
            "temperature": 0.8,
            "return_full_text": False
        },
        "options": {"wait_for_model": True}
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        for url in HF_MODELS:
            try:
                logging.info(f"Пробую модель: {url}")
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, list) and len(result) > 0:
                        raw_text = result[0].get('generated_text', '')
                        # Очистка текста от технических тегов
                        clean_text = raw_text.split("<|assistant|>")[-1].strip()
                        if clean_text:
                            return clean_text
                
                logging.warning(f"Модель {url} не подошла (Status: {response.status_code})")
                continue
                
            except Exception as e:
                logging.error(f"Ошибка при обращении к {url}: {e}")
                continue
        
        return "Даже все мои запасные процессоры сгорели от твоей тупости. Ошибка API у всех моделей."

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Калобот на Hugging Face запущен. Что тебе нужно, кусок мяса?")

@dp.message()
async def handle(message: types.Message):
    # Бот отвечает на любое сообщение в личке
    response_text = await get_hf_response(message.text)
    await message.answer(response_text)

# --- HEALTHCHECK СЕРВЕР ДЛЯ RENDER ---

async def handle_healthcheck(request):
    return web.Response(text="I'm alive.")

async def main():
    # Запуск веб-сервера для Render (чтобы не падал по таймауту)
    app = web.Application()
    app.router.add_get("/", handle_healthcheck)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 8080)))
    await site.start()

    # Очистка очереди сообщений перед запуском
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запуск бота
    logging.info("Бот запущен и готов к унижениям.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")
