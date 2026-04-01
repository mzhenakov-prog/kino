import asyncio
import sqlite3
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# --- КОНФИГ ---
API_TOKEN = '8381032154:AAEQdqCbxcGOuzunPWhPZbXaCjzaPpJbuhM'
TMDB_API_KEY = 'fdc70aa152320f85d8acdfda64b69b36'
ADMIN_ID = 5298604296
CHANNELS = [-1001888094511, -1003861409701] # ID твоих каналов
CHANNEL_LINKS = ["https://t.me/lyubimkatt", "https://t.me/kinoo_rum"]

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
conn = sqlite3.connect('bot_data.db', check_same_thread=False)
cursor = conn.cursor()
# Таблица для кэша фильмов и для юзеров (рефералка)
cursor.execute('CREATE TABLE IF NOT EXISTS movies (query TEXT PRIMARY KEY, title TEXT, rating REAL, overview TEXT, poster TEXT, link TEXT)')
cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, referrer_id INTEGER)')
conn.commit()

# --- ФУНКЦИИ ПРОВЕРКИ И ПОИСКА ---
async def check_sub(user_id):
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status == "left": return False
        except: return False
    return True

def get_movie(query):
    q = query.lower().strip()
    cursor.execute("SELECT * FROM movies WHERE query=?", (q,))
    cached = cursor.fetchone()
    if cached: return {'title': cached[1], 'rating': cached[2], 'overview': cached[3], 'poster': cached[4], 'link': cached[5]}

    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={q}&language=ru-RU"
    try:
        res = requests.get(url, timeout=5).json()
        if res.get('results'):
            m = res['results'][0]
            mv = {'title': m['title'], 'rating': m['vote_average'], 'overview': m['overview'], 'poster': m['poster_path'], 'link': f"https://www.themoviedb.org/movie/{m['id']}"}
            cursor.execute("INSERT OR REPLACE INTO movies VALUES (?, ?, ?, ?, ?, ?)", (q, mv['title'], mv['rating'], mv['overview'], mv['poster'], mv['link']))
            conn.commit()
            return mv
    except: return None

# --- ХЕНДЛЕРЫ ---
@dp.message(Command("start"))
async def start(m: types.Message, command: CommandObject):
    # Логика рефералки
    user_id = m.from_user.id
    ref_id = command.args if command.args and command.args.isdigit() else None
    
    cursor.execute("INSERT OR IGNORE INTO users (user_id, referrer_id) VALUES (?, ?)", (user_id, ref_id))
    conn.commit()

    if not await check_sub(user_id):
        kb = [[InlineKeyboardButton(text="Подписаться 1", url=CHANNEL_LINKS[0])],
              [InlineKeyboardButton(text="Подписаться 2", url=CHANNEL_LINKS[1])],
              [InlineKeyboardButton(text="✅ Я подписался", callback_data="check")]]
        await m.answer("❗ Для использования бота подпишитесь на наши каналы:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else:
        await m.answer("🔍 Введите название фильма!")

@dp.callback_query(F.data == "check")
async def check_callback(call: types.CallbackQuery):
    if await check_sub(call.from_user.id):
        await call.message.edit_text("✅ Спасибо за подписку! Теперь введите название фильма.")
    else:
        await call.answer("❌ Вы не подписались на все каналы!", show_alert=True)

@dp.message(F.text == "🔗 Рефералы")
async def ref_menu(m: types.Message):
    if m.from_user.id == ADMIN_ID:
        cursor.execute("SELECT COUNT(*) FROM users WHERE referrer_id IS NOT NULL")
        count = cursor.fetchone()[0]
        bot_user = await bot.get_me()
        link = f"https://t.me/{bot_user.username}?start={ADMIN_ID}"
        await m.answer(f"👤 <b>Админ-панель рефералов</b>\n\nВсего переходов по ссылкам: {count}\nВаша ссылка: <code>{link}</code>", parse_mode="HTML")

@dp.message()
async def search(m: types.Message):
    if not await check_sub(m.from_user.id):
        return await start(m, None)

    # Добавляем кнопку админа в обычное меню, если это ты
    kb_list = []
    if m.from_user.id == ADMIN_ID and m.text == "Панель":
        await ref_menu(m)
        return

    res = get_movie(m.text)
    if res:
        text = f"🍿 <b>{res['title']}</b>\n\n⭐️ Рейтинг: {res['rating']}\n\n{res['overview'][:500]}..."
        kb = [[InlineKeyboardButton(text="🎬 Смотреть фильм", url=res['link'])]]
        if m.from_user.id == ADMIN_ID:
            kb.append([InlineKeyboardButton(text="🔗 Рефералы", callback_data="none")]) # Просто индикация
            
        if res['poster']:
            await m.answer_photo(f"https://image.tmdb.org/t/p/w500{res['poster']}", caption=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")
        else:
            await m.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")
    else:
        await m.answer("❌ Фильм не найден.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
