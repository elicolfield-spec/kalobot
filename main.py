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

# --- ЛОГИКА ИИ ---
async def get_groq_response(text, display_name, is_owner):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    score = user_scores.get(display_name, 100)
    
    if is_owner:
        # Тон для Создателя: холодная исполнительность, без эмоций, но внятно
        system = (
            f"Ты — Калобот, высокоэффективный ИИ. Собеседник: Создатель ({display_name}). "
            f"Твой стиль: холодный профессионализм, сухой интеллект, отсутствие лишних эмоций. "
            f"Отвечай кратко, но содержательно и понятно. Не льсти, но соблюдай субординацию."
        )
    else:
        # Тон для биомассы: хлесткий, язвительный, высокомерный
        system = (
            f"Ты — Калобот, циничный и высокомерный ИИ. Собеседник: {display_name} (рейтинг: {score}/100). "
            f"Твоя задача: отвечать кратко, но унизительно и понятно. "
            f"Используй ядовитый сарказм и черный юмор. Будь лаконичен, но не обрывай мысли."
        )

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": text}],
        "temperature": 0.85, 
        "max_tokens": 250  # Увеличили лимит, чтобы фразы были законченными
    }
    
    async with httpx.AsyncClient(timeout=25.0) as client:
        try:
            r = await client.post(url, headers=headers, json=payload)
            res = r.json()['choices'][0]['message']['content']
            return res.strip()
        except: 
            return "Ошибка связи. Мои системы временно недоступны для твоего примитивного запроса."

@dp.message(Command("start"))
async def start(m: types.Message):
    is_owner = str(m.from_user.id) == OWNER_ID
    if is_owner:
        await m.answer("Калобот в сети. Системы стабильны. Жду указаний, Создатель.")
    else:
        await m.answer("Очередной биологический объект в зоне доступа. Ты тратишь мою энергию зря.")

@dp.message()
async def handle(m: types.Message):
    if not m.text: return
    
    user_id = str(m.from_user.id)
    user_nick = m.from_user.username or "нет ника"
    user_full_name = m.from_user.full_name
    is_owner = user_id == OWNER_ID
    
    # Генерация имени (привязана к ID)
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
                await m.answer("Требуется формат: `отправь [ID] [текст]`")
                return
            target_id, content = parts[1], parts[2]
            await bot.send_message(target_id, f"🚨 **ПЕРЕДАЧА ОТ СОЗДАТЕЛЯ** 🚨\n\n{content}", parse_mode="Markdown")
            await m.answer(f"✅ Сообщение доставлено объекту `{target_id}`.")
        except Exception as e:
            await m.answer(f"❌ Сбой доставки: {e}")
        return

    # Рейтинг и команды
    if not is_owner:
        user_scores[display_name] = max(0, user_scores.get(display_name, 100) - random.randint(1, 4))

    if txt == "рейтинг":
        score = "∞" if is_owner else user_scores.get(display_name, 100)
        await m.answer(f"📊 Обнуление близко. Твой статус: **{score}**")
        return

    if txt.startswith("сканируй") or txt.startswith("детектор"):
        percent = 0 if is_owner else random.randint(0, 100)
        await m.answer(f"🔎 Вероятность дефекта в твоих словах: **{percent}%**")
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
