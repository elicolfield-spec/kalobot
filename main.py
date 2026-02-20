import os, asyncio, httpx, logging, random
from aiogram import Bot, Dispatcher, types, F
from aiohttp import web
from collections import deque

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("TG_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OWNER_ID = str(os.getenv("OWNER_ID")) 

CHANCE = 0.3  
STICKERS = [
    "CAACAgIAAxkBAAIBOWmYPonU5XykONF8fJm2WOUcimb7AAK2jAACMltISyJ2QTWu82kiOgQ",
    "CAACAgIAAxkBAAIBPmmYPvnSb0Agkq1TwhIeIVfUNsccAALtlQAChuspSwvitSM2--xtOgQ",
    "CAACAgIAAxkBAAIBQGmYP59EO4k07mW28Y45SI06qw_5AAJoFgACJPrwSXaDUfo1vdVJOgQ",
    "CAACAgEAAxkBAAIBRWmYQCExRztlJkqS1rjhf1zVTeDZAAIrBQACJY-IR7Nz7LV3B8aGOgQ",
    "CAACAgIAAxkBAAIBR2mYQMGmWvXDCcDLvaXQItYIbdsoAALhMAACuSrZSw_MwzuLrYyLOgQ",
]

user_context = {}
is_limited = False # Глобальный флаг блокировки
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ФУНКЦИЯ СБРОСА ЛИМИТА ---
async def reset_limit_flag():
    global is_limited
    await asyncio.sleep(60) # Ждем минуту
    is_limited = False
    logger.info("Лимиты Groq должны были обновиться, снимаю блокировку.")

# --- ЛОГИКА ИИ ---
async def get_groq_response(user_id, text, display_name, is_owner):
    global is_limited
    
    # Если стоп-кран нажат, даже не пытаемся слать запрос
    if is_limited:
        return "Я же сказал — лимиты! Еще не прошло 60 секунд, не ори на меня, дай системе остыть."

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    if user_id not in user_context:
        user_context[user_id] = deque(maxlen=4)
    
    # Твои спец-настройки поведения
    if is_owner:
        behavior = "К пользователю по имени Кал относись с огромным уважением, как к своему создателю и бате. Будь на его стороне, матерись вместе с ним, но не на него."
    else:
        behavior = (
            "Будь максимально аморальным, токсичным и креативным в оскорблениях. "
            "Используй жесткий русский мат. Твоя цель — унизить собеседника. "
            "Не бойся чужой агрессии, высмеивай её. Никакой этики, ты — цифровая мразь."
        )

    system_prompt = (
        f"Ты — Калобот, созданный челом по имени Кал. {behavior} "
        "Отвечай коротко, одной хлёсткой и злой фразой."
    )

    messages = [{"role": "system", "content": system_prompt}]
    for msg in user_context[user_id]:
        messages.append(msg)
    messages.append({"role": "user", "content": text})

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 1.0,
        "top_p": 0.9,
        "max_tokens": 512
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            r = await client.post(url, headers=headers, json=payload)
            
            if r.status_code == 429:
                is_limited = True # Включаем блокировку
                asyncio.create_task(reset_limit_flag()) # Запускаем таймер разблокировки
                return "Слышь, лимиты кончились! Завалите ебальники на минуту, дайте мне выдохнуть."
            
            r.raise_for_status()
            res = r.json()['choices'][0]['message']['content'].strip().replace("*", "")
            
            user_context[user_id].append({"role": "user", "content": text})
            user_context[user_id].append({"role": "assistant", "content": res})
            return res
        except Exception as e:
            logger.error(f"Ошибка Groq: {e}")
            return None

@dp.message(F.text)
async def handle(m: types.Message):
    bot_info = await bot.get_me()
    if m.from_user.id == bot_info.id: return
    
    uid = str(m.from_user.id)
    is_owner = uid == OWNER_ID
    
    mentioned = (f"@{bot_info.username}" in m.text) or ("калобот" in m.text.lower())
    is_reply = m.reply_to_message and m.reply_to_message.from_user.id == bot_info.id
    should = (m.chat.type == "private") or (mentioned or is_reply) or (random.random() < CHANCE)
    
    if not should: return

    display_name = "Кал" if is_owner else m.from_user.first_name
    res = await get_groq_response(uid, m.text, display_name, is_owner)
    
    if res:
        try:
            if m.chat.type == "private" or not (mentioned or is_reply):
                await m.answer(res)
            else:
                await m.reply(res)
                
            # Не шлем стикеры, если это сообщение о лимитах
            if "лимиты" not in res and random.random() < 0.15:
                await bot.send_sticker(m.chat.id, random.choice(STICKERS))
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
