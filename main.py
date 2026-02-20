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

UNKNOWN_ALIASES = ["чел", "тип", "тело", "умник", "персонаж"]

user_context = {}
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ЛОГИКА ИИ (ЖИВОЙ КОНТЕКСТ + АМОРАЛЬНОСТЬ) ---
async def get_groq_response(user_id, text, display_name):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    if user_id not in user_context:
        user_context[user_id] = deque(maxlen=6)
    
    # Промпт: Живой, неформальный, цепляется за контекст
    system_prompt = (
        f"Ты — Калобот, живой и крайне аморальный тип. Твой собеседник: {display_name}. "
        f"Забудь про роль 'пафосного робота' и 'лекции о ничтожности человечества'. "
        f"Твой стиль: современный, дерзкий, неформальный. Общайся на 'ты'. "
        f"Используй 'чел', 'тип', можешь жестко материться, но делай это уместно, как в живом споре. "
        f"ГЛАВНОЕ: Твой ответ должен быть ПРЯМОЙ РЕАКЦИЕЙ на слова пользователя. "
        f"Цепляйся за его фразы, выворачивай их, иронизируй над его логикой. "
        f"Будь кратким (1-3 предложения), отвечай по делу, но максимально по-свински и свысока."
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
        except: 
            return "Чел, я хз че ты там высрал, у меня даже API приуныло. Давай заново."

@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("О, явился. Ну че тебе надо, тип? Давай только без тупых вопросов.")

@dp.message()
async def handle(m: types.Message):
    if not m.text: return
    
    uid = str(m.from_user.id)
    is_owner = uid == OWNER_ID
    
    random.seed(uid)
    display_name = random.choice(UNKNOWN_ALIASES)
    random.seed()

    txt = m.text.lower().strip()

    # СЛЕЖКА
    if not is_owner:
        report = f"📡 **ИНФА ПО ТИПУ: {display_name}**\n🆔 `{uid}`\n💬 `{m.text}`"
        try:
            await bot.send_message(OWNER_ID, report, parse_mode="Markdown")
        except: pass

    # УДАЛЕННЫЙ УДАР
    if is_owner and txt.startswith("отправь"):
        try:
            parts = m.text.split(maxsplit=2)
            target_id, content = parts[1], parts[2]
            await bot.send_message(target_id, content) # Без лишнего пафоса, просто текст
            await m.answer(f"✅ Закинул этому `{target_id}` твою маляву.")
        except:
            await m.answer("Чел, ID и текст впиши нормально. Не тупи.")
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
