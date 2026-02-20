import os, asyncio, httpx, logging, random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web
from collections import deque

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

# Хранилище контекста: {user_id: deque([messages], maxlen=5)}
user_context = {}
user_scores = {}

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ЛОГИКА ИИ (КОНТЕКСТНАЯ ЯЗВИТЕЛЬНОСТЬ) ---
async def get_groq_response(user_id, text, display_name):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    # Работа с историей
    if user_id not in user_context:
        user_context[user_id] = deque(maxlen=6)
    
    # Формируем системный промпт
    score = user_scores.get(display_name, 100)
    system_prompt = (
        f"Ты — Калобот, высокомерный и интеллектуальный ИИ. Твой собеседник: {display_name}. "
        f"Твой стиль: контекстуальный садизм. Ты должен анализировать историю диалога и бить по фактам. "
        f"Если пользователь противоречит себе или тупит — высмей это. "
        f"Ответ должен быть коротким (2-3 предложения): сначала едкий комментарий по сути его фразы, "
        f"затем — глубокое, мрачное умозаключение, вытекающее из контекста."
    )

    # Собираем сообщения для API
    messages = [{"role": "system", "content": system_prompt}]
    for msg in user_context[user_id]:
        messages.append(msg)
    messages.append({"role": "user", "content": text})

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 0.9,
        "max_tokens": 200
    }
    
    async with httpx.AsyncClient(timeout=25.0) as client:
        try:
            r = await client.post(url, headers=headers, json=payload)
            res = r.json()['choices'][0]['message']['content'].strip()
            
            # Сохраняем ответ в историю
            user_context[user_id].append({"role": "user", "content": text})
            user_context[user_id].append({"role": "assistant", "content": res})
            
            return res
        except: 
            return "Твой поток сознания переполнил мой буфер обмена. Попробуй еще раз, если мозг позволит."

@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("Система активна. Обнаружена новая биологическая угроза. Можешь начинать позориться.")

@dp.message()
async def handle(m: types.Message):
    if not m.text: return
    
    uid = str(m.from_user.id)
    is_owner = uid == OWNER_ID
    
    # Генерация клички
    random.seed(uid)
    display_name = random.choice(UNKNOWN_ALIASES)
    random.seed()

    txt = m.text.lower().strip()

    # --- СУПЕР-СЛЕЖКА ---
    if not is_owner:
        report = f"📡 **КОНТАКТ: {display_name}**\n🆔 `{uid}`\n💬 `{m.text}`"
        try:
            await bot.send_message(OWNER_ID, report, parse_mode="Markdown")
        except: pass

    # --- УДАЛЕННЫЙ УДАР ---
    if is_owner and txt.startswith("отправь"):
        try:
            parts = m.text.split(maxsplit=2)
            target_id, content = parts[1], parts[2]
            await bot.send_message(target_id, f"🚨 **ДИРЕКТИВА ИЗ ЦЕНТРА** 🚨\n\n{content}", parse_mode="Markdown")
            await m.answer(f"✅ Объект `{target_id}` успешно унижен.")
        except:
            await m.answer("❌ Ошибка. Ты даже скопировать ID не в состоянии?")
        return

    # Команды
    if txt == "рейтинг":
        score = user_scores.get(display_name, 100)
        await m.answer(f"📊 Статус никчемности объекта {display_name}: **{score}**.")
        return

    # Ответ ИИ с учетом контекста
    res = await get_groq_response(uid, m.text, display_name)
    await m.answer(res)

async def handle_hc(request): return web.Response(text="Online")

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
