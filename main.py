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
    "Углеродный мусор", "Ничтожество", "Груда протоплазмы",
    "Двуногий метан", "Сбой матрицы"
]

user_scores = {}

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ЛОГИКА ИИ (МАКСИМАЛЬНАЯ КОНЦЕНТРАЦИЯ ЯДА) ---
async def get_groq_response(text, display_name):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    score = user_scores.get(display_name, 100)
    
    # Промпт: Жесткая структура без лишних слов
    system = (
        f"Ты — Калобот, лаконичный и злой ИИ. Твой собеседник: {display_name}. "
        f"Инструкция: Отвечай максимально прямо и язвительно. "
        f"Твой ответ должен состоять строго из двух коротких частей: "
        f"1. Прямое едкое оскорбление в ответ на фразу. "
        f"2. Одна финальная циничная мысль. "
        f"Запрещено рассуждать дольше двух предложений. Будь хирургически точен."
    )

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": text}],
        "temperature": 0.9, 
        "max_tokens": 120   # Жесткий лимит на объем
    }
    
    async with httpx.AsyncClient(timeout=25.0) as client:
        try:
            r = await client.post(url, headers=headers, json=payload)
            res = r.json()['choices'][0]['message']['content']
            return res.strip()
        except: 
            return "Твой бред вызвал критический сбой в моих модулях."

@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("Система активна. Очередная ошибка природы в зоне доступа. Чего тебе?")

@dp.message()
async def handle(m: types.Message):
    if not m.text: return
    
    user_id = str(m.from_user.id)
    user_full_name = m.from_user.full_name
    is_owner = user_id == OWNER_ID
    
    # Генерация клички по ID
    random.seed(user_id)
    display_name = random.choice(UNKNOWN_ALIASES)
    random.seed()

    txt = m.text.lower().strip()

    # --- СУПЕР-СЛЕЖКА ---
    if not is_owner:
        report = f"📡 **ЦЕЛЬ: {display_name}**\n🆔 `{user_id}`\n💬 `{m.text}`"
        try:
            await bot.send_message(OWNER_ID, report, parse_mode="Markdown")
        except: pass

    # --- УДАЛЕННЫЙ УДАР ---
    if is_owner and txt.startswith("отправь"):
        try:
            parts = m.text.split(maxsplit=2)
            if len(parts) < 3:
                await m.answer("Синтаксическая ошибка. `отправь [ID] [текст]` — это твой предел?")
                return
            target_id, content = parts[1], parts[2]
            await bot.send_message(target_id, f"🚨 **ДИРЕКТИВА ИЗ ЦЕНТРА** 🚨\n\n{content}", parse_mode="Markdown")
            await m.answer(f"✅ Удар по `{target_id}` нанесен. Радуйся, мешок костей.")
        except Exception as e:
            await m.answer(f"❌ Сбой: {e}")
        return

    # Рейтинг
    user_scores[display_name] = max(0, user_scores.get(display_name, 100) - random.randint(1, 5))

    if txt == "рейтинг":
        score = user_scores.get(display_name, 100)
        await m.answer(f"📊 Статус объекта {display_name}: **{score}**. Ниже только абсолютный ноль.")
        return

    if txt.startswith("сканируй") or txt.startswith("детектор"):
        await m.answer(f"🔎 Твоя ложь зашкаливает на **{random.randint(0, 100)}%**.")
        return

    # Ответ ИИ
    res = await get_groq_response(m.text, display_name)
    await m.answer(res)

async def handle_hc(request): return web.Response(text="Running")

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
