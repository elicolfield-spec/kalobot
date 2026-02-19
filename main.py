import os
import asyncio
import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Всё самое необходимое
bot = Bot(token=os.getenv("TG_TOKEN"))
dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Привет! Я твой самый первый бот. Теперь я снова простой и рабочий!")

@dp.message()
async def handle(message: types.Message):
    # Прямой и простой запрос к нейронке
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            },
            json={
                "model": "google/gemini-2.0-flash-001", 
                "messages": [{"role": "user", "content": message.text}]
            }
        )
        data = response.json()
        text = data['choices'][0]['message']['content']
        await message.answer(text)

async def main():
    # Удаляем вебхук, чтобы не было конфликта при перезапуске
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
