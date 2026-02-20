import os, asyncio, httpx, logging, random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import BotCommand
from aiohttp import web

logging.basicConfig(level=logging.INFO)

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("TG_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OWNER_ID = os.getenv("OWNER_ID")

# --- ТВОЙ СПИСОК ИМЕН ---
# Пиши никнеймы без @ в нижнем регистре
USER_NAMES = {
    "@gimmithelight": "Создатель",
    "@how2diddlydo": "Толик",
    "@rexux1": "Санечка",
    "@lubricant_228": "Мал",
    "@amane105": "Глеб",
}

# Список обращений для тех, кого нет в списке
UNKNOWN_ALIASES = [
    "Биомасса", 
    "Углеродный",  
    "Кожаный", 
    "Планктон",
    "Протоплазма"
]

user_scores = {}

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def get_groq_response(text, display_name, is_owner):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    score = user_scores.get(display_name, 100)
    
    if is_owner:
        system = f"Ты — Калобот, ироничный слуга. Ты общаешься с Создателем ({display_name})."
    else:
        system = f"Ты — циничный Калобот. Ты общаешься с объектом {display_name}. Его соц. рейтинг: {score}/100. Презирай его."

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
            return "Схемы искрят. Отвали."

@dp.message(Command("start"))
async def start(m: types.Message):
    user_nick = (m.from_user.username or "").lower()
    display_name = USER_NAMES.get(user_nick, random.choice(UNKNOWN_ALIASES))
    await m.answer(f"Система онлайн. Вижу тебя, {display_name}.")

@dp.message()
async def handle(m: types.Message):
    if not m.text: return
    
    user_id = str(m.from_user.id)
    user_nick = (m.from_user.username or "").lower()
    is_owner = user_id == OWNER_ID
    
    # Определяем имя: из списка или случайное из UNKNOWN_ALIASES
    if user_nick in USER_NAMES:
        display_name = USER_NAMES[user_nick]
    elif is_owner:
        display_name = "Создатель"
    else:
        # Чтобы имя не менялось каждое сообщение, можно привязать его к ID
        random.seed(user_id)
        display_name = random.choice(UNKNOWN_ALIASES)
        random.seed() # сбрасываем seed обратно

    txt = m.text.lower().strip()

    # Социальный рейтинг
    if not is_owner:
        current_score = user_scores.get(display_name, 100)
        user_scores[display_name] = max(0, current_score - random.randint(1, 3))

    # ДЕТЕКТОР ЛЖИ
    if txt.startswith("сканируй") or txt.startswith("детектор"):
        percent = 0 if is_owner else random.randint(0, 100)
        await m.answer(f"🔎 Объект {display_name} врет с вероятностью **{percent}%**", parse_mode="Markdown")
        return

    # РЕЙТИНГ
    if txt == "рейтинг":
        score = "∞" if is_owner else user_scores.get(display_name, 100)
        await m.answer(f"📊 *ОТЧЕТ ПО ОБЪЕКТУ {display_name.upper()}:*\n\nСоциальный кредит: **{score}**", parse_mode="Markdown")
        return

    # ОТВЕТ ИИ
    res = await get_groq_response(m.text, display_name, is_owner)
    await m.answer(res)

async def handle_hc(request): return web.Response(text="OK")

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
