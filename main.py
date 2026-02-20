import os, asyncio, httpx, logging, random, datetime, sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiohttp import web
from collections import deque

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("TG_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OWNER_ID = str(os.getenv("OWNER_ID")) 
TARGET_USER_ID = os.getenv("TARGET_USER_ID") 

CHANCE = 0.3  
STICKERS = [
    "CAACAgIAAxkBAAIBOWmYPonU5XykONF8fJm2WOUcimb7AAK2jAACMltISyJ2QTWu82kiOgQ",
    "CAACAgIAAxkBAAIBPmmYPvnSb0Agkq1TwhIeIVfUNsccAALtlQAChuspSwvitSM2--xtOgQ",
    "CAACAgIAAxkBAAIBQGmYP59EO4k07mW28Y45SI06qw_5AAJoFgACJPrwSXaDUfo1vdVJOgQ",
    "CAACAgEAAxkBAAIBRWmYQCExRztlJkqS1rjhf1zVTeDZAAIrBQACJY-IR7Nz7LV3B8aGOgQ",
    "CAACAgIAAxkBAAIBR2mYQMGmWvXDCcDLvaXQItYIbdsoAALhMAACuSrZSw_MwzuLrYyLOgQ",
]

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect("bot_data.db")
    conn.execute("CREATE TABLE IF NOT EXISTS members (chat_id TEXT, user_id TEXT, first_name TEXT, PRIMARY KEY (chat_id, user_id))")
    conn.execute("CREATE TABLE IF NOT EXISTS msg_logs (chat_id TEXT, user_id TEXT, username TEXT, timestamp DATETIME)")
    conn.commit()
    conn.close()

user_context = {}
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ЛОГИКА ИИ ---
async def get_groq_response(user_id, text, display_name, is_owner, system_override=None):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    if user_id not in user_context:
        user_context[user_id] = deque(maxlen=4)
    
    owner_info = "Твой создатель — Кал. Ты его уважаешь. Остальные — мусор."
    
    system_prompt = (
        f"Ты — Калобот, грубый и токсичный. {owner_info} "
        "Стиль: жесткий русский мат без цензуры. Отвечай кратко (1 фраза). "
        f"Собеседник: {display_name}."
    )
    
    sys_prompt = system_override if system_override else system_prompt

    payload = {
        "model": "llama3-8b-8192", # Поменял на 8B для стабильности лимитов
        "messages": [{"role": "system", "content": sys_prompt}] + list(user_context[user_id]) + [{"role": "user", "content": text}],
        "temperature": 1.0,
        "top_p": 0.9
    }
    
    async with httpx.AsyncClient(timeout=25.0) as client:
        for attempt in range(3): # Пробуем 3 раза при ошибке 429
            try:
                r = await client.post(url, headers=headers, json=payload)
                if r.status_code == 429:
                    logger.warning("Лимит исчерпан, жду 2 сек...")
                    await asyncio.sleep(2)
                    continue
                
                r.raise_for_status()
                res = r.json()['choices'][0]['message']['content'].strip().replace("*", "")
                
                if not system_override:
                    user_context[user_id].append({"role": "user", "content": text})
                    user_context[user_id].append({"role": "assistant", "content": res})
                return res
            except Exception as e:
                logger.error(f"Ошибка Groq: {e}")
                break
    return None

# --- ФУНКЦИИ РАССЫЛКИ ---
async def naruto_mailing():
    if not TARGET_USER_ID: return
    while True:
        await asyncio.sleep(3600)
        fact = await get_groq_response("sys_naruto", "Дай факт про Наруто", "Система", False, "Ты Калобот. Дай факт про Наруто коротко и без мата.")
        if fact:
            try: await bot.send_message(TARGET_USER_ID, f"Факт по Наруто:\n\n{fact}")
            except: pass

@dp.message(F.text)
async def handle(m: types.Message):
    bot_info = await bot.get_me()
    if m.from_user.id == bot_info.id: return
    
    uid, cid = str(m.from_user.id), str(m.chat.id)
    is_owner = uid == OWNER_ID
    
    # БД логика
    try:
        conn = sqlite3.connect("bot_data.db")
        conn.execute("INSERT INTO msg_logs VALUES (?, ?, ?, ?)", (cid, uid, m.from_user.username, datetime.datetime.now()))
        if m.chat.type != "private":
            conn.execute("INSERT OR REPLACE INTO members VALUES (?, ?, ?)", (cid, uid, m.from_user.first_name))
        conn.commit()
        conn.close()
    except: pass

    # Рассуди
    if m.text.lower().startswith("калобот рассуди"):
        try:
            conn = sqlite3.connect("bot_data.db")
            res = conn.execute("SELECT user_id, username FROM msg_logs WHERE chat_id = ? ORDER BY timestamp DESC LIMIT 1", (cid,)).fetchone()
            conn.close()
            if res:
                name = f"@{res[1]}" if res[1] else f"ID:{res[0]}"
                await m.answer(f"Рассудил. Пидарас дня — {name}. Свободен.")
        except: pass
        return

    # Ответ ИИ
    mentioned = (f"@{bot_info.username}" in m.text) or ("калобот" in m.text.lower())
    is_reply = m.reply_to_message and m.reply_to_message.from_user.id == bot_info.id
    should = (m.chat.type == "private") or (mentioned or is_reply) or (random.random() < CHANCE)
    
    if not should: return

    display_name = "Кал (Отец)" if is_owner else m.from_user.first_name
    res = await get_groq_response(uid, m.text, display_name, is_owner)
    
    if res:
        if m.chat.type == "private" or not (mentioned or is_reply):
            await m.answer(res)
        else:
            await m.reply(res)
        if random.random() < 0.2:
            try: await bot.send_sticker(cid, random.choice(STICKERS))
            except: pass

async def handle_hc(request): return web.Response(text="Alive")

async def main():
    init_db()
    app = web.Application(); app.router.add_get("/", handle_hc)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 8080))).start()
    asyncio.create_task(naruto_mailing())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
