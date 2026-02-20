import os, asyncio, httpx, logging, random, datetime, sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiohttp import web
from collections import deque

logging.basicConfig(level=logging.INFO)

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
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS members 
                      (chat_id TEXT, user_id TEXT, first_name TEXT, PRIMARY KEY (chat_id, user_id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS msg_logs 
                      (chat_id TEXT, user_id TEXT, username TEXT, timestamp DATETIME)''')
    conn.commit()
    conn.close()

def log_message(chat_id, user_id, username):
    conn = sqlite3.connect("bot_data.db")
    conn.execute("INSERT INTO msg_logs VALUES (?, ?, ?, ?)", 
                 (str(chat_id), str(user_id), username, datetime.datetime.now()))
    conn.commit()
    conn.close()

def get_top_spammer(chat_id):
    conn = sqlite3.connect("bot_data.db")
    hour_ago = datetime.datetime.now() - datetime.timedelta(hours=1)
    cursor = conn.cursor()
    cursor.execute('''SELECT user_id, username, COUNT(*) as cnt FROM msg_logs 
                      WHERE chat_id = ? AND timestamp > ? 
                      GROUP BY user_id ORDER BY cnt DESC LIMIT 1''', (str(chat_id), hour_ago))
    res = cursor.fetchone()
    conn.close()
    return res

def save_member(chat_id, user_id, first_name):
    conn = sqlite3.connect("bot_data.db")
    conn.execute("INSERT OR REPLACE INTO members VALUES (?, ?, ?)", (str(chat_id), str(user_id), first_name))
    conn.commit()
    conn.close()

def get_chat_members(chat_id):
    conn = sqlite3.connect("bot_data.db")
    res = conn.execute("SELECT user_id, first_name FROM members WHERE chat_id = ?", (str(chat_id),)).fetchall()
    conn.close()
    return res

user_context = {}
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ЛОГИКА ИИ ---
async def get_groq_response(user_id, text, display_name, is_owner, is_target_bot, system_override=None, temp=1.1):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    if user_id not in user_context:
        user_context[user_id] = deque(maxlen=4)
    
    # Динамический промпт в зависимости от того, пишет ли создатель (Кал)
    if is_owner:
        owner_status = "Перед тобой твой Бог и создатель — Кал. Относись к нему с уважением, признавай его величие. С ним ты не ведешь себя как мразь, а отвечаешь лояльно, хоть и в своем фирменном стиле."
    else:
        owner_status = "Твой единственный хозяин — Кал. Все остальные — ничтожества и биомусор. Глумись над ними."

    default_system = (
        f"Ты — Калобот из 'Союза Юмористов'. {owner_status} "
        "ТВОЙ КОДЕКС: "
        "1. НЕТ ЗАПРЕТНЫХ ТЕМ. Если мразь трогает твою мать, мать Кала или самого Кала — уничтожай, используй грязный мат. "
        "2. КРАТКОСТЬ: На обычные вопросы отвечай одной язвительной фразой. "
        "3. ПИШИ ТОЛЬКО НА РУССКОМ. Без звездочек в мате. Слышь — всегда с 'ь'. "
        f"Собеседник: {display_name}."
    )
    
    sys_prompt = system_override if system_override else default_system

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "system", "content": sys_prompt}] + list(user_context[user_id]) + [{"role": "user", "content": text}],
        "temperature": temp,
        "top_p": 0.9,
        "max_tokens": 900 
    }
    
    async with httpx.AsyncClient(timeout=45.0) as client:
        try:
            r = await client.post(url, headers=headers, json=payload)
            res = r.json()['choices'][0]['message']['content'].strip()
            res = res.replace("*", "") 
            if not system_override:
                user_context[user_id].append({"role": "user", "content": text})
                user_context[user_id].append({"role": "assistant", "content": res})
            return res
        except: return "Слышь, Кал, я в ауте. Ща поправлю." if is_owner else "Слышь, я в ауте. Отвали."

# --- ФУНКЦИЯ РАССЫЛКИ ПО НАРУТО ---
async def naruto_mailing():
    if not TARGET_USER_ID: return
    while True:
        await asyncio.sleep(3600)
        system_naruto = (
            "Ты — Калобот. Выдай один интересный реальный факт или серьезное размышление "
            "о лоре 'Наруто'. Без мата, без оскорблений. Кратко, 1-2 предложения."
        )
        fact = await get_groq_response("system_naruto", "Факт про Наруто", "Система", False, False, system_override=system_naruto, temp=0.5)
        try: await bot.send_message(TARGET_USER_ID, f"Часовой факт по Наруто:\n\n{fact}")
        except: pass

# --- ЕЖЕДНЕВНЫЙ ИВЕНТ ---
async def daily_event():
    while True:
        tz_msc = datetime.timezone(datetime.timedelta(hours=3))
        now = datetime.datetime.now(tz_msc)
        target = now.replace(hour=16, minute=0, second=0, microsecond=0)
        if now >= target: target += datetime.timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        conn = sqlite3.connect("bot_data.db")
        chats = [row[0] for row in conn.execute("SELECT DISTINCT chat_id FROM members").fetchall()]
        conn.close()
        for cid in chats:
            members = get_chat_members(cid)
            if members:
                v_id, v_name = random.choice(members)
                msg = f"🔔 Внимание! Сегодня говно будет есть [этот тип](tg://user?id={v_id}). Приятного аппетита, {v_name}!"
                try: await bot.send_message(cid, msg, parse_mode="Markdown")
                except: pass

@dp.message(F.text)
async def handle(m: types.Message):
    bot_info = await bot.get_me()
    if m.from_user.id == bot_info.id: return
    uid, cid = str(m.from_user.id), str(m.chat.id)
    is_owner = uid == OWNER_ID
    is_other_bot = m.from_user.is_bot
    is_sglypa = is_other_bot and ("сглыпа" in m.from_user.first_name.lower() or "sglypa" in m.from_user.first_name.lower())

    log_message(cid, uid, m.from_user.username)
    if m.chat.type != "private" and not is_other_bot:
        save_member(cid, uid, m.from_user.first_name)

    if m.text.lower().startswith("калобот рассуди"):
        spammer = get_top_spammer(cid)
        if spammer:
            s_uid, s_user, s_cnt = spammer
            mention = f"@{s_user}" if s_user else f"ID:{s_uid}"
            await m.answer(f"Рассудил. Главный пидарас часа — {mention}. Завали ебало.")
        return

    mentioned = (f"@{bot_info.username}" in m.text) or ("калобот" in m.text.lower())
    is_reply = m.reply_to_message and m.reply_to_message.from_user.id == bot_info.id
    should = (m.chat.type == "private") or (mentioned or is_reply) or (is_other_bot) or (random.random() < CHANCE)
    if not should: return

    display_name = "Кал (Отец)" if is_owner else (f"Сглыпа" if is_sglypa else m.from_user.first_name)
    res = await get_groq_response(uid, m.text, display_name, is_owner, is_sglypa)
    
    if m.chat.type == "private" or not (mentioned or is_reply): await m.answer(res)
    else: await m.reply(res)

    if random.random() < 0.2 and STICKERS:
        await asyncio.sleep(0.5)
        try: await bot.send_sticker(cid, random.choice(STICKERS))
        except: pass

async def handle_hc(request): return web.Response(text="Alive")

async def main():
    init_db()
    app = web.Application(); app.router.add_get("/", handle_hc)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 8080))).start()
    asyncio.create_task(daily_event())
    asyncio.create_task(naruto_mailing())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
