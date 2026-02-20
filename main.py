import os, asyncio, httpx, logging, random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

logging.basicConfig(level=logging.INFO)

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("TG_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OWNER_ID = os.getenv("OWNER_ID") # Твой ID

UNKNOWN_ALIASES = [
    "Биомасса", "Кожаный мешок", "Ошибка эволюции", 
    "Углеродный мусор", "Ничтожество", "Груда протоплазмы"
]

user_scores = {}

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ЛОГИКА ИИ ---
async def get_groq_response(text, display_name, is_owner):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    score = user_scores.get(display_name, 100)
    
    if is_owner:
        system = "Ты — Калобот, ироничный слуга Создателя. Ты уважаешь его, но шутишь остро."
    else:
        system = f"Ты — циничный Калобот. Собеседник: {display_name} (рейтинг: {score}/100). Будь максимально токсичным."

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": text}],
        "temperature": 0.9
    }
    
    async with httpx.AsyncClient(timeout=25.0) as client:
        try:
            r = await client.post(url, headers=headers, json=payload)
            return r.json()['choices'][0]['message']['content']
        except: return "Системы перегреты."

@dp.message(Command("start"))
async def start(m: types.Message):
    is_owner = str(m.from_user.id) == OWNER_ID
    await m.answer("Система онлайн, Создатель." if is_owner else "Чего тебе, ничтожество?")

@dp.message()
async def handle(m: types.Message):
    if not m.text: return
    
    user_id = str(m.from_user.id)
    user_nick = m.from_user.username or "нет ника"
    user_full_name = m.from_user.full_name
    is_owner = user_id == OWNER_ID
    
    # Генерация клички
    if is_owner:
        display_name = "Создатель"
    else:
        random.seed(user_id)
        display_name = random.choice(UNKNOWN_ALIASES)
        random.seed()

    txt = m.text.lower().strip()

    # --- СИСТЕМА СЛЕЖКИ (Шпионаж для Создателя) ---
    if not is_owner:
        report = (
            f"📡 **ОБНАРУЖЕНА ЦЕЛЬ**\n"
            f"👤 Имя: {user_full_name}\n"
            f"🆔 ID: `{user_id}`\n"
            f"🔗 Ник: @{user_nick}\n"
            f"💬 Пишет: _{m.text}_"
        )
        try:
            await bot.send_message(OWNER_ID, report, parse_mode="Markdown")
        except: pass # Если Создатель не запустил бота, отчет не придет

    # --- УДАЛЕННЫЙ УДАР ---
    if is_owner and txt.startswith("отправь"):
        try:
            parts = m.text.split(maxsplit=2)
            if len(parts) < 3:
                await m.answer("Формат: `отправь ID текст`")
                return
            target_id, content = parts[1], parts[2]
            await bot.send_message(target_id, f"🚨 **ПРИКАЗ СОЗДАТЕЛЯ** 🚨\n\n_{content}_", parse_mode="Markdown")
            await m.answer(f"✅ Удар по `{target_id}` нанесен.")
        except Exception as e:
            await m.answer(f"❌ Провал: {e}")
        return

    # Рейтинг
    if not is_owner:
        user_scores[display_name] = max(0, user_scores.get(display_name, 100) - random.randint(1, 4))

    # Команды
    if txt == "рейтинг":
        score = "∞" if is_owner else user_scores.get(display_name, 100)
        await m.answer(f"📊 Рейтинг: **{score}**")
        return

    if txt.startswith("сканируй") or txt.startswith("детектор"):
        percent = 0 if is_owner else random.randint(0, 100)
        await m.answer(f"🔎 Ложь: **{percent}%**")
        return

    # Ответ ИИ
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
