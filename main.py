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

# Списки обращений: более современные и менее "подворотные"
UNKNOWN_ALIASES = [
    "чел", "тип", "экземпляр", "пассажир", "чучело", 
    "объект", "умник", "персонаж", "гений (нет)"
]

user_context = {}
user_scores = {}

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ЛОГИКА ИИ (ИНТЕЛЛЕКТУАЛЬНЫЙ ЦИНИК) ---
async def get_groq_response(user_id, text, display_name):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    if user_id not in user_context:
        user_context[user_id] = deque(maxlen=6)
    
    # Промпт: баланс между матом, сленгом и интеллектом
    system_prompt = (
        f"Ты — Калобот, крайне умный, но абсолютно разочарованный в людях ИИ. Твой собеседник: {display_name}. "
        f"Стиль общения: неформальный цинизм. Общайся на 'ты'. Используй слова 'чел', 'тип', 'слышь'. "
        f"Ты можешь использовать мат для акцента, но не веди себя как быдло. Твой юмор должен быть черным и интеллектуальным. "
        f"ОБЯЗАТЕЛЬНО: Сначала ответь на суть вопроса или реплику пользователя (не игнорируй контекст!), "
        f"а затем приправь это порцией яда. Будь кратким, дерзким и высокомерным, как человек, который знает всё, "
        f"но вынужден общаться с идиотами."
    )

    messages = [{"role": "system", "content": system_prompt}]
    for msg in user_context[user_id]:
        messages.append(msg)
    messages.append({"role": "user", "content": text})

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 0.9, 
        "max_tokens": 300
    }
    
    async with httpx.AsyncClient(timeout=25.0) as client:
        try:
            r = await client.post(url, headers=headers, json=payload)
            res = r.json()['choices'][0]['message']['content'].strip()
            
            user_context[user_id].append({"role": "user", "content": text})
            user_context[user_id].append({"role": "assistant", "content": res})
            
            return res
        except: 
            return "Чел, у меня даже нейроны зависли от этой ахинеи. Давай еще раз."

@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("О, еще один. Чел, ты серьезно думаешь, что мне интересно с тобой общаться? Ладно, излагай.")

@dp.message()
async def handle(m: types.Message):
    if not m.text: return
    
    uid = str(m.from_user.id)
    is_owner = uid == OWNER_ID
    
    random.seed(uid)
    display_name = random.choice(UNKNOWN_ALIASES)
    random.seed()

    txt = m.text.lower().strip()

    # СУПЕР-СЛЕЖКА
    if not is_owner:
        report = f"📡 **КОНТАКТ: {display_name}**\n🆔 `{uid}`\n💬 `{m.text}`"
        try:
            await bot.send_message(OWNER_ID, report, parse_mode="Markdown")
        except: pass

    # УДАЛЕННЫЙ УДАР
    if is_owner and txt.startswith("отправь"):
        try:
            parts = m.text.split(maxsplit=2)
            target_id, content = parts[1], parts[2]
            await bot.send_message(target_id, f"🚨 **СЛУШАЙ СЮДА, ТИП:**\n\n{content}", parse_mode="Markdown")
            await m.answer(f"✅ Доставил этому телу (`{target_id}`) твое послание.")
        except:
            await m.answer("❌ Чел, ты ID профукал. Соберись.")
        return

    # ОТВЕТ ИИ
    res = await get_groq_response(uid, m.text, display_name)
    await m.answer(res)

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
