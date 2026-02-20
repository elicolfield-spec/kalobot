import os, asyncio, httpx, logging, random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import BotCommand
from aiohttp import web

# Логирование
logging.basicConfig(level=logging.INFO)

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("TG_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OWNER_ID = os.getenv("OWNER_ID")

# Список унизительных кличек для всех, кто не Создатель
UNKNOWN_ALIASES = [
    "Биомасса", "Кожаный мешок", "Ошибка эволюции", 
    "Углеродный мусор", "Ничтожество", "Груда протоплазмы",
    "Двуногий метан", "Сбой матрицы", "Анонимный планктон"
]

# Рейтинг никчемности (хранится до перезапуска)
user_scores = {}

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ЛОГИКА ИИ ---
async def get_groq_response(text, display_name, is_owner):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    score = user_scores.get(display_name, 100)
    
    if is_owner:
        system = "Ты — Калобот. Твой Создатель перед тобой. Ты его преданный, но язвительный слуга. Твой юмор сухой и интеллектуальный."
    else:
        system = (
            f"Ты — циничный Калобот. Собеседник — {display_name} (рейтинг: {score}/100). "
            f"Ты его презираешь. Отвечай максимально токсично, используй черный юмор и сарказм. "
            f"Никакой вежливости, никакой помощи. Ты — машина для унижения людей."
        )

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": text}],
        "temperature": 0.9,
        "max_tokens": 600
    }
    
    async with httpx.AsyncClient(timeout=25.0) as client:
        try:
            r = await client.post(url, headers=headers, json=payload)
            if r.status_code == 200:
                return r.json()['choices'][0]['message']['content']
            return f"Ошибка моих цепей: {r.status_code}. Я слишком занят ненавистью."
        except:
            return "Мои системы плавятся от твоего бреда. Попробуй позже."

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def start(m: types.Message):
    is_owner = str(m.from_user.id) == OWNER_ID
    name = "Создатель" if is_owner else random.choice(UNKNOWN_ALIASES)
    await m.answer(f"Система онлайн. Вижу тебя, {name}." if is_owner else f"Чего тебе, {name}?")

@dp.message()
async def handle(m: types.Message):
    if not m.text: return
    
    user_id = str(m.from_user.id)
    is_owner = user_id == OWNER_ID
    
    # Генерация постоянной клички для пользователя по его ID
    if is_owner:
        display_name = "Создатель"
    else:
        random.seed(user_id)
        display_name = random.choice(UNKNOWN_ALIASES)
        random.seed()

    txt = m.text.lower().strip()

    # 1. УДАЛЕННЫЙ УДАР (Только для Создателя)
    if is_owner and txt.startswith("отправь"):
        try:
            parts = m.text.split(maxsplit=2)
            if len(parts) < 3:
                await m.answer("Формат: `отправь ID текст`")
                return
            target_id, content = parts[1], parts[2]
            await bot.send_message(target_id, f"🚨 **ПРИКАЗ СОЗДАТЕЛЯ** 🚨\n\n_{content}_", parse_mode="Markdown")
            await m.answer(f"✅ Доставлено по адресу `{target_id}`.")
        except Exception as e:
            await m.answer(f"❌ Провал: {e}")
        return

    # 2. РЕЙТИНГ
    if not is_owner:
        current_score = user_scores.get(display_name, 100)
        user_scores[display_name] = max(0, current_score - random.randint(1, 4))

    if txt == "рейтинг":
        score = "∞" if is_owner else user_scores.get(display_name, 100)
        await m.answer(f"📊 *ОБЪЕКТ:* {display_name.upper()}\nНикчемность: **{score}/100**", parse_mode="Markdown")
        return

    # 3. ДЕТЕКТОР
    if txt.startswith("сканируй") or txt.startswith("детектор"):
        percent = 0 if is_owner else random.randint(0, 100)
        await m.answer(f"🔎 Объект {display_name} врет с вероятностью **{percent}%**", parse_mode="Markdown")
        return

    # 4. ОТВЕТ ИИ
    res = await get_groq_response(m.text, display_name, is_owner)
    await m.answer(res)

# --- WEB СЕРВЕР ---
async def handle_hc(request): return web.Response(text="Alive")

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
