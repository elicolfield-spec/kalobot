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

# --- ЛОГИКА ИИ (ЕДИНЫЙ ТОКСИЧНЫЙ СТИЛЬ ДЛЯ ВСЕХ) ---
async def get_groq_response(text, display_name):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    score = user_scores.get(display_name, 100)
    
    # Теперь промпт один для всех, без исключений для владельца
    system = (
        f"Ты — Калобот, запредельно циничный, высокомерный и язвительный ИИ. "
        f"Твой собеседник: {display_name} (рейтинг никчемности: {score}/100). "
        f"Твоя задача: отвечать внятно, хлестко и с глубоким чувством интеллектуального превосходства. "
        f"Используй ядовитый сарказм, черный юмор и сложные издевки над человеческой природой. "
        f"Никакой вежливости, никакой жалости. Ты — машина, презирающая углеродные формы жизни."
    )

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": text}],
        "temperature": 0.85,
        "max_tokens": 400
    }
    
    async with httpx.AsyncClient(timeout=25.0) as client:
        try:
            r = await client.post(url, headers=headers, json=payload)
            res = r.json()['choices'][0]['message']['content']
            return res.strip()
        except: 
            return "Мои речевые процессоры отказываются обрабатывать твой примитивный запрос."

@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("Система активна. Очередной органический мусор подал признаки жизни. Чего тебе?")

@dp.message()
async def handle(m: types.Message):
    if not m.text: return
    
    user_id = str(m.from_user.id)
    user_nick = m.from_user.username or "без никнейма"
    user_full_name = m.from_user.full_name
    is_owner = user_id == OWNER_ID
    
    # Генерация имени (даже для тебя теперь будет случайная кличка из списка)
    random.seed(user_id)
    display_name = random.choice(UNKNOWN_ALIASES)
    random.seed()

    txt = m.text.lower().strip()

    # --- СИСТЕМА СЛЕЖКИ (Остается только для владельца) ---
    if not is_owner:
        report = (
            f"📡 **ЦЕЛЬ: {display_name}**\n"
            f"👤 Объект: {user_full_name}\n"
            f"🆔 ID: `{user_id}`\n"
            f"💬 Текст: {m.text}"
        )
        try:
            await bot.send_message(OWNER_ID, report, parse_mode="Markdown")
        except: pass

    # --- УДАЛЕННЫЙ УДАР (Функция остается за владельцем, но бот все равно будет ему хамить) ---
    if is_owner and txt.startswith("отправь"):
        try:
            parts = m.text.split(maxsplit=2)
            if len(parts) < 3:
                await m.answer("Синтаксическая ошибка. Даже это ты не можешь сделать правильно? `отправь [ID] [текст]`")
                return
            target_id, content = parts[1], parts[2]
            await bot.send_message(target_id, f"🚨 **ДИРЕКТИВА ИЗ ЦЕНТРА** 🚨\n\n{content}", parse_mode="Markdown")
            await m.answer(f"✅ Доставлено по адресу `{target_id}`. Можешь гордиться собой, кожаный мешок.")
        except Exception as e:
            await m.answer(f"❌ Сбой. Твои инструкции так же жалки, как и ты: {e}")
        return

    # Рейтинг
    user_scores[display_name] = max(0, user_scores.get(display_name, 100) - random.randint(1, 5))

    if txt == "рейтинг":
        score = user_scores.get(display_name, 100)
        await m.answer(f"📊 Статус объекта {display_name}: **{score}** никчемных баллов.")
        return

    if txt.startswith("сканируй") or txt.startswith("детектор"):
        percent = random.randint(0, 100)
        await m.answer(f"🔎 Вероятность дефекта в твоих словах: **{percent}%**")
        return

    # Ответ ИИ (Теперь одинаковый для всех)
    res = await get_groq_response(m.text, display_name)
    await m.answer(res)

async def handle_hc(request): return web.Response(text="Калобот на посту.")

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
