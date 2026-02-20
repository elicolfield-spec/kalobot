import os, asyncio, httpx, logging, random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, BotCommand
from aiohttp import web

# Логирование
logging.basicConfig(level=logging.INFO)

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("TG_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OWNER_ID = os.getenv("OWNER_ID")

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def get_groq_response(text, is_owner):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    system = "Ты циничный робот Калобот. Ненавидишь людей." if not is_owner else "Ты ироничный слуга Создателя."
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": text}],
        "temperature": 0.8
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            r = await client.post(url, headers=headers, json=payload)
            if r.status_code == 200:
                return r.json()['choices'][0]['message']['content']
            return f"Ошибка API: {r.status_code}"
        except: return "Схемы замкнуло, не могу говорить."

@dp.message(Command("start"))
async def start(m: types.Message):
    is_owner = str(m.from_user.id) == OWNER_ID
    await m.answer("Система онлайн. Слушаю, Создатель." if is_owner else "Чего тебе, кожаный?")

@dp.message()
async def handle(m: types.Message):
    if not m.text: return
    is_owner = str(m.from_user.id) == OWNER_ID
    txt = m.text.lower().strip()

    # СЕКРЕТНАЯ КОМАНДА: ЗАКАЗ ЕДЫ
    if "закажи еду" in txt:
        seed = random.randint(1, 99999)
        # Формируем запрос для картинки
        img_url = f"https://image.pollinations.ai/prompt/disgusting_prison_slop_canteen_food_tray_realistic?seed={seed}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(img_url)
                if response.status_code == 200:
                    # Бот САМ скачал картинку и теперь отправляет её как файл
                    photo = BufferedInputFile(response.content, filename="food.jpg")
                    await m.answer_photo(photo=photo, caption="Твой хрючево-сет готов. Жри, не обляпайся.")
                else:
                    await m.answer(f"Повар спит. Ошибка сервиса: {response.status_code}")
            return
        except Exception as e:
            logging.error(f"Error generating food: {e}")
            await m.answer("Повар сбежал в другую вселенную. Попробуй позже.")
            return

    # Обычный ответ ИИ
    res = await get_groq_response(m.text, is_owner)
    await m.answer(res)

# --- СЕРВЕР ДЛЯ RENDER ---
async def handle_hc(request):
    return web.Response(text="Калобот активен")

async def main():
    app = web.Application()
    app.router.add_get("/", handle_hc)
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Используем порт из настроек
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    await bot.set_my_commands([BotCommand(command="start", description="Пробудить")])
    await bot.delete_webhook(drop_pending_updates=True)
    
    logging.info(f"Бот запущен на порту {port}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
