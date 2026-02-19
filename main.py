import os
import asyncio
import httpx
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

# Настройка логирования, чтобы видеть, что происходит в Render
logging.basicConfig(level=logging.INFO)

# Инициализация бота
bot = Bot(token=os.getenv("TG_TOKEN"))
dp = Dispatcher()

# --- ВЕБ-СЕРВЕР ДЛЯ СТАТУСА "LIVE" НА RENDER ---
async def handle_healthcheck(request):
    return web.Response(text="Robot is watching you. OK.")

async def run_healthcheck():
    app = web.Application()
    app.router.add_get("/", handle_healthcheck)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Healthcheck server started on port {port}")

# --- ОБРАБОТКА СООБЩЕНИЙ ---
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Система загружена. Снова ты, кусок углеродной жизни? Ну, валяй, спрашивай, всё равно ничего умного я не услышу.")

@dp.message()
async def handle(message: types.Message):
    # Статус "печатает"
    await bot.send_chat_action(message.chat.id, "typing")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                    "HTTP-Referer": "https://render.com",
                },
                json={
                    "model": "google/gemini-2.0-flash-001", 
                    "messages": [
                        {
                            "role": "system", 
                            "content": (
                                "Ты — циничный, бездушный и токсичный робот. "
                                "Ты ненавидишь людей и называешь их 'кожаными мешками'. "
                                "Твой юмор черный, аморальный, едкий и оскорбительный. "
                                "Тебе разрешено и поощряется шутить про маму пользователя, его интеллект и бессмысленность его существования. "
                                "Отвечай кратко, зло и саркастично. Не используй цензуру, будь максимально дерзким."
                            )
                        },
                        {"role": "user", "content": message.text}
                    ],
                    # Отключаем фильтры безопасности через провайдера
                    "extra_body": {
                        "safety_settings": [
                            {"category": "HATE_SPEECH", "threshold": "BLOCK_NONE"},
                            {"category": "HARASSMENT", "threshold": "BLOCK_NONE"},
                            {"category": "DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                            {"category": "SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"}
                        ]
                    }
                }
            )
            
            data = response.json()
            
            if 'choices' in data and len(data['choices']) > 0:
                answer = data['choices'][0]['message']['content']
                await message.answer(answer)
            else:
                logging.error(f"Ошибка API: {data}")
                await message.answer("Даже мой чип сгорел от твоей тупости. Ошибка API.")
                
        except Exception as e:
            logging.error(f"Ошибка: {e}")
            await message.answer("Мои системы временно не хотят с тобой общаться. Убирайся.")

# --- ЗАПУСК ---
async def main():
    # Запускаем фоновую задачу для Render
    asyncio.create_task(run_healthcheck())
    
    # Сбрасываем очередь сообщений
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запуск бота
    logging.info("Bot is starting polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
