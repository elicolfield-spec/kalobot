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
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    system = "Ты циничный Калобот. Ненавидишь людей." if not is_owner else "Ты ироничный слуга Создателя."
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": text}],
        "temperature": 0.8
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            r = await client.post(url, headers=headers, json=payload)
            return r.json()['choices'][0]['message']['content']
        except:
            return "Схемы замкнуло. Отвали."

@dp.message(Command("start"))
async def start(m: types.Message):
    is_owner = str(m.from_user.id) == OWNER_ID
    await m.answer("Система онлайн. Слушаю, Создатель." if is_owner else "Чего тебе, кожаный?")

@dp.message()
async def handle(m: types.Message):
    if not m.text: return
    is_owner = str(m.from_user.id) == OWNER_ID
    txt = m.text.lower().strip()

    if txt.startswith("сканируй") or txt.startswith("детектор"):
        if is_owner:
            await m.answer("🔍 *Сканирование Создателя...*\n\nРезультат: **100% ПРАВДА**.", parse_mode="Markdown")
        else:
            percent = random.randint(0, 100)
            verdicts = ["Ты врешь как дышишь.", "Правды меньше 1%.", "Датчики забиты ложью.", "Наглая ложь!"]
            await m.answer(f"🔎 *Детектор лжи...*\n\nВероятность лжи: **{percent}%**\nВердикт: _{random.choice(verdicts)}_", parse_mode="Markdown")
        return

    res = await get_groq_response(m.text, is_owner)
    await m.answer(res)

async def handle_hc(request):
    return web.Response(text="Alive")

async def main():
    app = web.Application()
    app.router.add_get("/", handle_hc)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    await web.TCPSite(runner, "0.0.0.0", port).start()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
