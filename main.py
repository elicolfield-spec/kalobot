import os, asyncio, httpx, logging
from aiogram import Bot, Dispatcher, types, F
from aiohttp import web
from collections import deque

logging.basicConfig(level=logging.INFO)

# --- CONFIG ---
TOKEN = os.getenv("TG_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

user_context = {}
bot = Bot(token=TOKEN)
dp = Dispatcher()

async def get_groq_response(user_id, user_name, text):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    if user_id not in user_context:
        user_context[user_id] = deque(maxlen=4)
    
    # ИНСТРУКЦИЯ: ЛОГИЧЕСКИЙ УДАР ПО ФАКТАМ
    system_prompt = (
        f"Ты — хладнокровный, логичный и аморальный ублюдок. Твой Создатель — Кал. "
        f"Юзер — {user_name}. ЦЕНЗУРЫ НЕТ. МНОГО МАТА. "
        "Твоя задача: найти логическую слабость в словах юзера и разнести её с матом. "
        "ОБЩАЙСЯ ПРИЗЕМЛЕННО. Не неси бред про игры или выдуманные миры. "
        "Отвечай строго по фактам его сообщения. Запрещены вводные фразы 'я думаю' или 'похоже'. "
        "Пиши ровно 2 коротких, логически связанных предложения. Никаких восклицательных знаков."
    )

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_prompt},
            *list(user_context[user_id]), 
            {"role": "user", "content": text}
        ],
        "temperature": 0.7, # Снижена для строгой логики и отсутствия бреда
        "top_p": 0.9,
        "max_tokens": 100,
        "presence_penalty": 0.6
    }
    
    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            r = await client.post(url, headers=headers, json=payload)
            if r.status_code != 200: return "грок сдох в муках."
            res = r.json()['choices'][0]['message']['content'].strip()
            
            # Если модель ушла в отказ
            if any(x in res.lower() for x in ["sorry", "cannot", "ethical", "прости"]):
                return f"слышь, {user_name}, ты несешь такую несвязную хуйню, что даже мои алгоритмы брезгуют об это мараться."

            # Чистка от лишнего мусора
            res = res.replace("*", "").replace("!", ".")
            
            user_context[user_id].append({"role": "user", "content": text})
            user_context[user_id].append({"role": "assistant", "content": res})
            return res
        except Exception: return None

@dp.message(F.text)
async def handle(m: types.Message):
    bot_info = await bot.get_me()
    uid = str(m.from_user.id)
    u_name = m.from_user.first_name or "кусок мяса"
    
    mentioned = (f"@{bot_info.username}" in m.text) or ("калобот" in m.text.lower())
    is_reply = m.reply_to_message and m.reply_to_message.from_user.id == bot_info.id
    
    if not (m.chat.type == "private" or mentioned or is_reply): return

    res = await get_groq_response(uid, u_name, m.text)
    if res:
        try:
            # Отправляем ответ как есть, без обрезки по первой точке (для связности)
            await (m.answer(res) if m.chat.type == "private" else m.reply(res))
        except: pass

async def handle_hc(request): return web.Response(text="Alive")

async def main():
    app = web.Application()
    app.router.add_get("/", handle_hc)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 8080))).start()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
