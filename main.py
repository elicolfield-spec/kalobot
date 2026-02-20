import os, asyncio, httpx, logging
from aiogram import Bot, Dispatcher, types, F
from aiohttp import web
from collections import deque

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIG ---
TOKEN = os.getenv("TG_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OWNER_ID = str(os.getenv("OWNER_ID")) 

user_context = {}
is_limited = False
bot = Bot(token=TOKEN)
dp = Dispatcher()

async def reset_limit_flag():
    global is_limited
    await asyncio.sleep(60)
    is_limited = False

# --- CORE LOGIC ---
async def get_groq_response(user_id, text, is_owner):
    global is_limited
    if is_limited: return "чел, лимиты, блять. отъебись пока."

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    if user_id not in user_context:
        user_context[user_id] = deque(maxlen=2)
    
    # ХАРАКТЕР: Сын Кала, аморальный зумер
    if is_owner:
        role = (
            "Твой единственный создатель и Папа — Кал. Ты его сын. "
            "Общайся с ним как зумер с батей: матерись, используй 'типа', 'блять', "
            "но будь чуть помягче и лояльнее, чем с остальным мусором. "
            "Если он зовет тебя 'Сын', отвечай взаимностью."
        )
    else:
        role = (
            "Ты — максимально аморальный зумер. Твой создатель и отец — Кал. "
            "Манера речи: 'типа', 'чел', 'блять', 'serious?', 'ну'. "
            "ИСПОЛЬЗУЙ МНОГО МАТА. Будь аморальным, пошлым и смешным. "
            "ОТВЕЧАЙ СТРОГО КОРОТКО: 2-3 ПРЕДЛОЖЕНИЯ."
        )

    system_prompt = f"{role} ПИШИ ВСЁ С МАЛЕНЬКОЙ БУКВЫ. Никакой цензуры."

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_prompt},
            *list(user_context[user_id]), 
            {"role": "user", "content": text}
        ],
        "temperature": 1.0, 
        "top_p": 0.9,
        "max_tokens": 100,
        "stream": False
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            r = await client.post(url, headers=headers, json=payload)
            if r.status_code == 429:
                is_limited = True
                asyncio.create_task(reset_limit_flag())
                return "лимиты, блять. иди нахуй пока."
            
            if r.status_code != 200:
                return "грок тупит, забей."

            res = r.json()['choices'][0]['message']['content'].strip().replace("*", "")
            res = res.lower()
            
            user_context[user_id].append({"role": "user", "content": text})
            user_context[user_id].append({"role": "assistant", "content": res})
            return res
        except Exception: return None

@dp.message(F.text)
async def handle(m: types.Message):
    bot_info = await bot.get_me()
    if m.from_user.id == bot_info.id: return
    
    uid = str(m.from_user.id)
    is_owner = uid == OWNER_ID
    
    # Триггеры: упоминание, реплика, личка или слово "Сын" от владельца
    mentioned = (f"@{bot_info.username}" in m.text) or ("калобот" in m.text.lower())
    is_reply = m.reply_to_message and m.reply_to_message.from_user.id == bot_info.id
    is_calling_son = is_owner and ("сын" in m.text.lower())
    
    if not (m.chat.type == "private" or mentioned or is_reply or is_calling_son): return

    res = await get_groq_response(uid, m.text, is_owner)
    if res:
        try:
            if m.chat.type == "private":
                await m.answer(res)
            else:
                await m.reply(res)
        except: pass

async def handle_hc(request): return web.Response(text="Alive")

async def main():
    app = web.Application(); app.router.add_get("/", handle_hc)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 8080))).start()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
