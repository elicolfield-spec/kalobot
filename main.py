import os, asyncio, httpx, logging, random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import BotCommand
from aiohttp import web

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TG_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OWNER_ID = os.getenv("OWNER_ID")

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def get_groq_response(text, is_owner):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    system = "Ты циничный робот Калобот." if not is_owner else "Ты ироничный слуга Создателя."
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": text}]
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            r = await client.post(url, headers=headers, json=payload)
            return r.json()['choices'][0]['message']['content']
        except: return "Схемы замкнуло..."

@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("Система онлайн." if str(m.from_user.id) == OWNER_ID else "Чего тебе?")

@dp.message()
async def handle(m: types.Message):
    if not m.text: return
    is_owner = str(m.from_user.id) == OWNER_ID
    txt = m.text.lower().strip()

    if "закажи еду" in txt:
        seed = random.randint(1, 99999)
        url = f"https://image.pollinations.ai/prompt/disgusting_slop_prison_food_tray?seed={seed}"
        try:
            await m.answer_photo(photo=url, caption="Твой заказ, ничтожество.")
            return
        except:
            await m.answer("Повар сбежал.")
            return

    res = await get_groq_response(m.text, is_owner)
    await m.answer(res)

async def main():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="OK"))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    await web.TCPSite(runner, "0.0.0.0", port).start()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
