import os
import asyncio
import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

# Инициализация
bot = Bot(token=os.getenv("TG_TOKEN"))
dp = Dispatcher()

# --- ТЕ САМЫЕ СТРОЧКИ ДЛЯ RENDER ---
async def handle_healthcheck(request):
    return web.Response(text="OK")

async def run_healthcheck():
    app = web.Application()
    app.router.add_get("/", handle_healthcheck)
    runner = web.AppRunner(app)
    await runner.setup()
    # Берем порт, который дает Render, или 8080 по умолчанию
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
# ----------------------------------

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Бот официально запущен и подтвержден системой Render! ✅")

@dp.message()
async def handle(message: types.Message):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
            json={
                "model": "google/gemini-2.0-flash-001", 
                "messages": [{"role": "user", "content": message.text}]
            }
        )
        data = response.json()
        text = data['choices'][0]['message']['content']
        await message.answer(text)

async def main():
    # Запускаем проверку порта в фоновом режиме
    asyncio.create_task(run_healthcheck())
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
