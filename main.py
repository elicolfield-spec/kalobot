import os
import asyncio
import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Настройки (всего два ключа)
TG_TOKEN = os.getenv("TG_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

bot = Bot(token=TG_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("Привет! Я снова в строю и готов к общению. Спрашивай что угодно!")

@dp.message()
async def handle_message(message: types.Message):
    # Статус "печатает" для реализма
    await bot.send_chat_action(message.chat.id, "typing")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "HTTP-Referer": "https://render.com", # Обязательно для OpenRouter
                },
                json={
                    "model": "deepseek/deepseek-chat", # Самая надежная модель на текущий момент
                    "messages": [{"role": "user", "content": message.text}]
                }
            )
            
            # Разбираем ответ
            data = response.json()
            answer = data['choices'][0]['message']['content']
            await message.answer(answer)

    except Exception as e:
        await message.answer("Упс, что-то пошло не так на стороне нейросети. Попробуй еще раз через минуту!")
        print(f"Ошибка: {e}")

async def main():
    # Сброс старых обновлений, чтобы не было конфликтов
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
