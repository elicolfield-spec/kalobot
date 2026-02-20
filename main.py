import os, asyncio, httpx, logging, random, datetime, sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiohttp import web
from collections import deque

logging.basicConfig(level=logging.INFO)

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("TG_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OWNER_ID = os.getenv("OWNER_ID")

CHANCE = 0.07 
ANSWER_PROBABILITY = 0.7

STICKERS = [
    "CAACAgIAAxkBAAIBOWmYPonU5XykONF8fJm2WOUcimb7AAK2jAACMltISyJ2QTWu82kiOgQ",
    "CAACAgIAAxkBAAIBPmmYPvnSb0Agkq1TwhIeIVfUNsccAALtlQAChuspSwvitSM2--xtOgQ",
    "CAACAgIAAxkBAAIBQGmYP59EO4k07mW28Y45SI06qw_5AAJoFgACJPrwSXaDUfo1vdVJOgQ",
    "CAACAgEAAxkBAAIBRWmYQCExRztlJkqS1rjhf1zVTeDZAAIrBQACJY-IR7Nz7LV3B8aGOgQ",
    "CAACAgIAAxkBAAIBR2mYQMGmWvXDCcDLvaXQItYIbdsoAALhMAACuSrZSw_MwzuLrYyLOgQ",
]

# --- РАБОТА С БАЗОЙ ДАННЫХ ---
def init_db():
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS members 
                      (chat_id TEXT, user_id TEXT, first_name TEXT, PRIMARY KEY (chat_id, user_id))''')
    conn.commit()
    conn.close()

def save_member(chat_id, user_id, first_name):
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO members (chat_id, user_id, first_name) VALUES (?, ?, ?)", 
                   (str(chat_id), str(user_id), first_name))
    conn.commit()
    conn.close()

def get_chat_members(chat_id):
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, first_name FROM members WHERE chat_id = ?", (str(chat_id),))
    rows = cursor.fetchall()
    conn.close()
    return rows

user_context = {}
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ЛОГИКА ИИ ---
async def get_groq_response(user_id, text, display_name, is_owner):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    if user_id not in user_context:
        user_context[user_id] = deque(maxlen=4)
    
    identity_status = "Перед тобой твой создатель Кал. Узнавай его, будь дерзким, но признавай его авторитет." if is_owner else ""
    
    system_prompt = (
        f"Ты — Калобот, член 'Союза Юмористов'. {identity_status} "
        f"Стиль: аморальный подонок, жесткий мат. "
        f"ГЛАВНОЕ: Отвечай ОЧЕНЬ кратко (1-2 предложения). Только чистый текст. "
        f"ЗАПРЕТ: Никаких ASCII артов и рисования символами. О создателе Кале говори только по прямому вопросу. "
        f"Собеседник: {display_name}. Слышь — всегда с 'ь'."
    )

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "system", "content": system_prompt}] + list(user_context[user_id]) + [{"role": "user", "content": text}],
        "temperature": 1.0, "max_tokens": 120
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            r = await client.post(url, headers=headers, json=payload)
            res = r.json()['choices'][0]['message']['content'].strip()
            user_context[user_id].append({"role": "user", "content": text})
            user_context[user_id].append({"role": "assistant", "content": res})
            return res
        except: return "Слышь, я в ауте. Отвали."

# --- ЕЖЕДНЕВНЫЙ ИВЕНТ (16:00 МСК) ---
async def daily_event():
    while True:
        tz_msc = datetime.timezone(datetime.timedelta(hours=3))
        now = datetime.datetime.now(tz_msc)
        target = now.replace(hour=16, minute=0, second=0, microsecond=0)
        
        if now >= target:
            target += datetime.timedelta(days=1)
        
        wait_seconds = (target - now).total_seconds()
        logging.info(f"Ивент запланирован через {wait_seconds/3600:.2f} ч.")
        await asyncio.sleep(wait_seconds)
        
        conn = sqlite3.connect("bot_data.db")
        chats = [row[0] for row in conn.execute("SELECT DISTINCT chat_id FROM members").fetchall()]
        conn.close()

        for cid in chats:
            members = get_chat_members(cid)
            if members:
                v_id, v_name = random.choice(members)
                # ОБНОВЛЕННЫЙ ТЕКСТ:
                msg = f"🔔 Внимание, уроды! По решению Калобота Союза Юмористов, сегодня говно будет есть [этот тип](tg://user?id={v_id}). Приятного аппетита, {v_name}!"
                try: await bot.send_message(cid, msg, parse_mode="Markdown")
                except: pass

@dp.message(F.text)
async def handle(m: types.Message):
    if m.from_user.is_bot: return
    
    uid, cid = str(m.from_user.id), str(m.chat.id)
    is_owner = uid == OWNER_ID
    
    if m.chat.type != "private":
        save_member(cid, uid, m.from_user.first_name)

    bot_info = await bot.get_me()
    mentioned = (f"@{bot_info.username}" in m.text) or ("калобот" in m.text.lower())
    is_reply = m.reply_to_message and m.reply_to_message.from_user.id == bot_info.id
    
    if m.chat.type == "private": should = True
    elif mentioned or is_reply: should = random.random() < ANSWER_PROBABILITY
    else: should = random.random() < CHANCE

    if not should: return

    display_name = "Отец" if is_owner else m.from_user.first_name
    res = await get_groq_response(uid, m.text, display_name, is_owner)
    
    if random.random() < 0.2: await m.answer(res)
    else: await m.reply(res)

    if random.random() < 0.25 and STICKERS:
        await asyncio.sleep(0.7)
        try: await bot.send_sticker(m.chat.id, random.choice(STICKERS))
        except: pass

async def handle_hc(request): return web.Response(text="Living")

async def main():
    init_db()
    asyncio.create_task(daily_event())
    app = web.Application()
    app.router.add_get("/", handle_hc)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 8080))).start()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
