import asyncio
import os
import logging
import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Настройка логирования, чтобы видеть ошибки в панели Logs
logging.basicConfig(level=logging.INFO)

# Читаем токены из секретов Space
TG_TOKEN = os.getenv("TG_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Если ключи забыли добавить, бот выдаст ошибку в консоль
if not TG_TOKEN or not OPENROUTER_API_KEY:
    raise ValueError("ОШИБКА: Токены TG_TOKEN или OPENROUTER_API_KEY не найдены в Settings -> Secrets!")

bot = Bot(token=TG_TOKEN)
dp = Dispatcher()

async def get_ai_response(text):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://huggingface.co/spaces", 
            },
            json={
                "model": "openrouter/auto", # Та самая бесплатная модель
                "messages": [{"role": "user", "content": text}]
            },
            timeout=60.0
        )
        data = response.json()
        if 'choices' in data:
            return data['choices'][0]['message']['content']
        else:
            logging.error(f"Ошибка OpenRouter: {data}")
            return "Извини, нейросеть прислала пустой ответ. Проверь ключи."

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("✅ Бот запущен и готов к работе! Спрашивай что угодно.")

@dp.message()
async def chat(message: types.Message):
    if not message.text: return
    
    await bot.send_chat_action(message.chat.id, "typing")
    
    try:
        answer = await get_ai_response(message.text)
        await message.reply(answer)
    except Exception as e:
        logging.error(f"Ошибка в чате: {e}")
        await message.reply("⚠️ Ошибка связи с ИИ. Попробуй позже.")

async def main():
    logging.info("Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
