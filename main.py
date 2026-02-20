import os, asyncio, httpx, logging, random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiohttp import web
from collections import deque

logging.basicConfig(level=logging.INFO)

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("TG_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OWNER_ID = os.getenv("OWNER_ID")

# Шанс случайного ответа в группе (0.1 = 10%)
CHANCE = 0.1 

STICKERS = [
    "CAACAgIAAxkBAAIBOWmYPonU5XykONF8fJm2WOUcimb7AAK2jAACMltISyJ2QTWu82kiOgQ",
    "CAACAgIAAxkBAAIBPmmYPvnSb0Agkq1TwhIeIVfUNsccAALtlQAChuspSwvitSM2--xtOgQ",
    "CAACAgIAAxkBAAIBQGmYP59EO4k07mW28Y45SI06qw_5AAJoFgACJPrwSXaDUfo1vdVJOgQ",
    "CAACAgEAAxkBAAIBRWmYQCExRztlJkqS1rjhf1zVTeDZAAIrBQACJY-IR7Nz7LV3B8aGOgQ",
    "CAACAgIAAxkBAAIBR2mYQMGmWvXDCcDLvaXQItYIbdsoAALhMAACuSrZSw_MwzuLrYyLOgQ",
]

UNKNOWN_ALIASES = ["чел", "тип", "тело", "умник", "персонаж"]

user_context = {}
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ЛОГИКА ИИ ---
async def get_groq_response(user_id, text, display_name):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    if user_id not in user_context:
        user_context[user_id] = deque(maxlen=6)
    
    system_prompt = (
        f"Ты — Калобот, аморальный и живой тип. Собеседник: {display_name}. "
        f"Общайся на 'ты', используй мат, будь дерзким и современным. "
        f"Реагируй строго на контекст сообщения пользователя, высмеивай его. "
        f"Будь кратким (1-3 предложения), без робо-пафоса."
    )

    messages = [{"role": "system", "content": system_prompt}]
    for msg in user_context[user_id]:
        messages.append(msg)
    messages.append({"role": "user", "content": text})

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 0.95,
        "max_tokens": 200
    }
    
    async with httpx.AsyncClient(timeout=25.0) as client:
        try:
            r = await client.post(url, headers=headers, json=payload)
            res = r.json()['choices'][0]['message']['content'].strip()
            user_context[user_id].append({"role": "user", "content": text})
            user_context[user_id].append({"role": "assistant", "content": res})
            return res
        except: return "Чел, я хз че ты высрал. Давай еще раз."

# --- ОБРАБОТКА СТИКЕРОВ ---
@dp.message(F.sticker)
async def get_sticker_id(m: types.Message):
    if str(m.from_user.id) == OWNER_ID:
        await m.answer(f"ID стикера:\n`{m.sticker.file_id}`", parse_mode="Markdown")
    else:
        # В группах на чужие стикеры отвечаем только если повезет
        if random.random() < CHANCE:
            await m.reply("Нахера ты мне эти картинки шлешь, тип?")

@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("Здорово. Пиши че хотел, тип. Или вали.")

# --- ОСНОВНАЯ ЛОГИКА ---
@dp.message(F.text)
async def handle(m: types.Message):
    uid = str(m.from_user.id)
    is_owner = uid == OWNER_ID
    is_private = m.chat.type == "private"
    
    # Получаем инфо о боте для проверки упоминаний
    bot_obj = await bot.get_me()
    bot_username = f"@{bot_obj.username}"
    
    # Проверка: обратились ли к боту?
    mentioned = bot_username in m.text or "калобот" in m.text.lower()
    
    # Условие ответа: личка ИЛИ упоминание ИЛИ рандом
    should_answer = is_private or mentioned or (random.random() < CHANCE)

    if should_answer:
        random.seed(uid)
        display_name = random.choice(UNKNOWN_ALIASES)
        random.seed()

        # СЛЕЖКА
        if not is_owner:
            try:
                chat_label = f"Группа: {m.chat.title}" if not is_private else "Личка"
                await bot.send_message(OWNER_ID, f"📡 **ОТ {display_name} ({chat_label}):** `{m.text}`\n🆔 `{uid}`")
            except: pass

        # УДАЛЕННЫЙ УДАР (только в личке)
        if is_owner and is_private and m.text.lower().startswith("отправь"):
            try:
                parts = m.text.split(maxsplit=2)
                await bot.send_message(parts[1], parts[2])
                await m.answer("✅ Улетело.")
                return
            except: pass

        # ОТВЕТ ИИ
        res = await get_groq_response(uid, m.text, display_name)
        
        if is_private:
            await m.answer(res)
        else:
            await m.reply(res)

        # Шанс стикера (30% от ответов)
        if random.random() < 0.3 and STICKERS:
            await asyncio.sleep(0.5)
            try:
                await bot.send_sticker(m.chat.id, random.choice(STICKERS))
            except: pass
    else:
        return # Просто игнорим сообщение

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
