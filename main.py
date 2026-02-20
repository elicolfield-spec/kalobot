import os
import asyncio
import httpx
import logging
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import BotCommand
from aiohttp import web

logging.basicConfig(level=logging.INFO)

# --- CONFIG ---
TOKEN = os.getenv("TG_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OWNER_ID = os.getenv("OWNER_ID")

bot = Bot(token=TOKEN)
dp = Dispatcher()

DEFAULT_PROMPT = "Ты — циничный робот 'Калобот'. Ненавидишь людей. Твой юмор черный. Отвечай кратко на русском."
OWNER_PROMPT = "Перед тобой твой Создатель. Ты по-прежнему саркастичный, но признаешь его авторитет. Отвечай иронично, но лояльно."

async def get_groq_response(user_text, is_owner):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    prompt = OWNER_PROMPT if is_owner else DEFAULT_PROMPT
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": user_text}],
        "temperature": 0.8
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            r = await client.post(url, headers=headers, json=payload)
            if r.status_code == 200:
                return r.json()['choices'][0]['message']['content']
            return f"Ошибка API: {r.status_code}"
        except Exception as e:
            return f"Ошибка: {str(e)}"

@dp.message(Command("start"))
async def start(message: types.Message):
    is_owner = str(message.from_user.id) == OWNER_ID
    text = "Система активна. Слушаю, Создатель." if is_owner else "Чего тебе, кожаный?"
    await message.answer(text)

@dp.message()
async def handle(message: types.Message):
    if not message.text: return
    is_owner = str(message.from_user.id) == OWNER_ID
    user_text = message.text.lower().strip()

    if "закажи еду" in user_text:
        balanda = "disgusting school cafeteria food, mystery gray sludge, slimy industrial leftovers, plastic tray, ultra-realistic"
        seed = random.randint(1, 99999)
        url = f"https://image.pollinations.ai/prompt/{balanda.replace(' ', '%20')}?seed={seed}"
        try:
            await message.answer_photo(photo=url, caption="Твой заказ готов. Приятного аппетита (нет).")
            return
        except:
            await message.answer("Повар сбежал.")
            return

    response = await get_groq_response(message.text, is_owner)
    await message.answer(response)

async def handle_hc(request):
    return web.Response(text="OK")

async def main():
    app = web.Application()
    app.router.add_get("/", handle_hc)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 8080)))
    await site.start()
    await bot.set_my_commands([BotCommand(command="start", description="Запуск")])
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
