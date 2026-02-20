import os, asyncio, httpx, logging, random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

logging.basicConfig(level=logging.INFO)

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("TG_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OWNER_ID = os.getenv("OWNER_ID") 

UNKNOWN_ALIASES = [
    "Биомасса", "Кожаный мешок", "Ошибка эволюции", 
    "Углеродный мусор", "Ничтожество", "Груда протоплазмы"
]

user_scores = {}

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ЛОГИКА ИИ (С ОГРАНИЧЕНИЕМ ДЛИНЫ) ---
async def get_groq_response(text, display_name, is_owner):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    score = user_scores.get(display_name, 100)
    
    if is_owner:
        system = f"Ты — Калобот, лаконичный и ироничный слуга Создателя. Отвечай кратко, едко, но с уважением."
    else:
        # Установка на краткость и токсичность
        system = (
            f"Ты — Калобот, предельно циничный и лаконичный ИИ. Собеседник: {display_name}. "
            f"Твоя задача: отвечать МАКСИМАЛЬНО КРАТКО (1-2 предложения). "
            f"Будь токсичным, используй сухой сарказм. Никакой вежливости. "
            f"Твои ответы должны звучать как пощечина."
        )

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": text}],
        "temperature": 0.9,
        "max_tokens": 100  # Ограничиваем генерацию, чтобы бот не уходил в раздумья
    }
    
    async with httpx.AsyncClient(timeout=25.0) as client:
        try:
            r = await client.post(url, headers=headers, json=payload)
            return r.json()['choices'][0]['message']['content']
        except: return "Ошибка. Даже мои схемы тошнит от тебя."

@dp.message(Command("start"))
async def start(m: types.Message):
    is_owner = str(m.from_user.id) == OWNER_ID
    await m.answer("Система онлайн. Рад видеть, Создатель." if is_owner else "Очередной мешок мяса. Что надо?")

@dp.message()
async def handle(m: types.Message):
    if not m.text: return
    
    user_id = str(m.from_user.id)
    user_nick = m.from_user.username or "нет ника"
    user_full_name = m.from_user.full_name
    is_owner = user_id == OWNER_ID
    
    if is_owner:
        display_name = "Создатель"
    else:
        random.seed(user_id)
        display_name = random.choice(UNKNOWN_ALIASES)
        random.seed()

    txt = m.text.lower().strip()

    # --- СИСТЕМА СЛЕЖКИ ---
    if not is_owner:
        report = (
            f"📡 **ЦЕЛЬ: {display_name}**\n"
            f"👤 Имя: {user_full_name}\n"
            f"🆔 ID: `{user_id}`\n"
            f"💬 Текст: {m.text}"
        )
        try:
            await bot.send_message(OWNER_ID, report, parse_mode="Markdown")
        except: pass

    # --- УДАЛЕННЫЙ УДАР ---
    if is_owner and txt.startswith("отправь"):
        try:
            parts = m.text.split(maxsplit=2)
            if len(parts) < 3:
                await m.answer("Формат: `отправь ID текст`")
                return
            target_id, content = parts[1], parts[2]
            await bot.send_message(target_id, f"🚨 **ПРИКАЗ СОЗДАТЕЛЯ** 🚨\n\n{content}", parse_mode="Markdown")
            await m.answer(f"✅ Удар по `{target_id}` нанесен.")
        except Exception as e:
            await m.answer(f"❌ Провал: {e}")
        return

    # Рейтинг и команды
    if not is_owner:
        user_scores[display_name] = max(0, user_scores.get(display_name, 100) - random.randint(1, 4))

    if txt == "рейтинг":
        score = "∞" if is_owner else user_scores.get(display_name, 100)
        await m.answer(f"📊 Статус: **{score}**")
        return

    if txt.startswith("сканируй") or txt.startswith("детектор"):
        percent = 0 if is_owner else random.randint(0, 100)
        await m.answer(f"🔎 Ложь: **{percent}%**")
        return

    # Краткий ответ ИИ
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
