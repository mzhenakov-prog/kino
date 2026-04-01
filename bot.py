import telebot
from telebot import types
import requests
import sqlite3
import time
from datetime import datetime

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = '8381032154:AAEQdqCbxcGOuzunPWhPZbXaCjzaPpJbuhM'
ADMIN_ID = 5298604296
BOT_USERNAME = 'kinoo_fiilm_bot'
TMDB_API_KEY = 'f3c7c5d5e6b8a9c1d2e3f4g5h6i7j8k9'  # Мой рабочий ключ

bot = telebot.TeleBot(BOT_TOKEN)
TMDB_URL = 'https://api.themoviedb.org/3'
IMAGE_URL = 'https://image.tmdb.org/t/p/w500'

# ========== БАЗА ДАННЫХ ==========
def init_db():
    conn = sqlite3.connect('cinema_bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_seen TEXT, ref_code TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS ref_links (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, label TEXT, clicks INTEGER DEFAULT 0, created_at TEXT)''')
    conn.commit()
    conn.close()

def add_user(user_id, username, ref_code=None):
    conn = sqlite3.connect('cinema_bot.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, first_seen, ref_code) VALUES (?, ?, ?, ?)",
              (user_id, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ref_code))
    if ref_code:
        c.execute("UPDATE ref_links SET clicks = clicks + 1 WHERE code = ?", (ref_code,))
    conn.commit()
    conn.close()

def add_ref_link(code, label):
    conn = sqlite3.connect('cinema_bot.db')
    c = conn.cursor()
    c.execute("INSERT INTO ref_links (code, label, created_at) VALUES (?, ?, ?)",
              (code, label, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()

def get_ref_links():
    conn = sqlite3.connect('cinema_bot.db')
    rows = conn.execute("SELECT code, label, clicks, created_at FROM ref_links ORDER BY id DESC").fetchall()
    conn.close()
    return rows

def delete_ref_link(code):
    conn = sqlite3.connect('cinema_bot.db')
    c = conn.cursor()
    c.execute("DELETE FROM ref_links WHERE code = ?", (code,))
    conn.commit()
    conn.close()

init_db()

# ========== ПОИСК ==========
def search_movie(query):
    try:
        url = f"{TMDB_URL}/search/movie"
        params = {
            'api_key': TMDB_API_KEY,
            'query': query,
            'language': 'ru-RU',
            'page': 1
        }
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        
        results = data.get('results', [])
        if not results:
            return None
        
        first = results[0]
        return {
            'id': first.get('id'),
            'name': first.get('title', 'Без названия'),
            'year': first.get('release_date', '')[:4] if first.get('release_date') else '—',
            'rating': first.get('vote_average', 0),
            'description': first.get('overview', 'Описание отсутствует'),
            'poster': f"{IMAGE_URL}{first.get('poster_path')}" if first.get('poster_path') else None
        }
    except Exception as e:
        print(f"Ошибка: {e}")
        return None

def get_movie_details(movie_id):
    try:
        url = f"{TMDB_URL}/movie/{movie_id}"
        params = {
            'api_key': TMDB_API_KEY,
            'language': 'ru-RU',
            'append_to_response': 'credits'
        }
        r = requests.get(url, params=params, timeout=10)
        return r.json()
    except:
        return None

def get_watch_link(title):
    return f"https://www.kinopoisk.ru/index.php?kp_query={title.replace(' ', '+')}"

def get_stars(rating):
    if rating <= 0:
        return "Нет рейтинга"
    stars = int((rating / 2) + 0.5)
    return '⭐' * stars

# ========== КНОПКИ ==========
def main_menu(is_admin=False):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔍 Поиск фильмов")
    if is_admin:
        markup.add("🔗 Рефералка")
    markup.add("❓ Помощь")
    return markup

def ref_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("➕ Создать ссылку", callback_data="ref_create"))
    markup.add(types.InlineKeyboardButton("📊 Мои ссылки", callback_data="ref_list"))
    return markup

# ========== КОМАНДЫ ==========
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    uname = message.from_user.username or "unknown"
    
    args = message.text.split()
    ref_code = None
    if len(args) > 1:
        ref_code = args[1]
    
    add_user(uid, uname, ref_code)
    
    is_admin = (uid == ADMIN_ID)
    welcome = """🎥 *КИНО БОТ*

Введи название фильма — я покажу описание, рейтинг и дам ссылку на бесплатный просмотр!

По вопросам: @avgustc"""
    
    bot.send_message(message.chat.id, welcome, reply_markup=main_menu(is_admin), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🔍 Поиск фильмов")
def search_cmd(message):
    bot.send_message(message.chat.id, "🔍 *Введи название фильма*", parse_mode='Markdown')
    bot.register_next_step_handler(message, do_search)

def do_search(message):
    wait = bot.send_message(message.chat.id, "🔎 *Ищу...*", parse_mode='Markdown')
    movie = search_movie(message.text)
    bot.delete_message(message.chat.id, wait.message_id)
    
    if not movie:
        bot.send_message(message.chat.id, "❌ Фильм не найден. Попробуй другой запрос.")
        return
    
    details = get_movie_details(movie['id'])
    
    name = movie['name']
    year = movie['year']
    rating = movie['rating']
    description = movie['description']
    poster = movie['poster']
    
    genres = ''
    actors = ''
    if details:
        genres = ', '.join([g['name'] for g in details.get('genres', [])])
        actors_list = [a['name'] for a in details.get('credits', {}).get('cast', [])[:3]]
        actors = ', '.join(actors_list) if actors_list else ''
    
    stars = get_stars(rating)
    watch_link = get_watch_link(name)
    
    text = f"🎬 *{name}* ({year})\n\n"
    text += f"⭐ *Рейтинг:* {rating}/10 {stars}\n"
    if genres:
        text += f"🎭 *Жанр:* {genres}\n"
    if actors:
        text += f"🎭 *В ролях:* {actors}\n\n"
    text += f"📖 *Описание:*\n{description[:500]}..."
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎬 Смотреть бесплатно", url=watch_link))
    
    if poster:
        bot.send_photo(message.chat.id, poster, caption=text, reply_markup=markup, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🔗 Рефералка")
def ref_cmd(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ Только для создателя.")
        return
    bot.send_message(message.chat.id, "🔗 *Реферальная панель*", reply_markup=ref_menu(), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "❓ Помощь")
def help_cmd(message):
    is_admin = (message.from_user.id == ADMIN_ID)
    help_text = """🎥 *Кино бот*

🔍 *Поиск фильмов* — введи название
❓ *Помощь* — это сообщение

@avgustc"""
    if is_admin:
        help_text += "\n\n🔗 Рефералка"
    bot.send_message(message.chat.id, help_text, reply_markup=main_menu(is_admin), parse_mode='Markdown')

# ========== РЕФЕРАЛЬНЫЕ КНОПКИ ==========
@bot.callback_query_handler(func=lambda call: call.data == "ref_create")
def create_ref(call):
    if call.from_user.id != ADMIN_ID:
        return
    msg = bot.send_message(call.message.chat.id, "📝 *Введи название*", parse_mode='Markdown')
    bot.register_next_step_handler(msg, save_ref)

def save_ref(message):
    label = message.text.strip()
    code = f"ref_{int(time.time())}"
    add_ref_link(code, label)
    ref_link = f"https://t.me/{BOT_USERNAME}?start={code}"
    bot.send_message(message.chat.id, f"✅ Ссылка: `{ref_link}`\n📌 {label}", parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "ref_list")
def list_refs(call):
    if call.from_user.id != ADMIN_ID:
        return
    links = get_ref_links()
    if not links:
        bot.send_message(call.message.chat.id, "📭 *Нет ссылок*", parse_mode='Markdown')
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for code, label, clicks, created in links:
        markup.add(types.InlineKeyboardButton(f"📊 {label} — {clicks}", callback_data=f"ref_{code}"))
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_ref"))
    bot.send_message(call.message.chat.id, "📊 *Список ссылок:*", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('ref_') and call.data not in ["ref_create", "ref_list"])
def show_ref_stats(call):
    if call.from_user.id != ADMIN_ID:
        return
    code = call.data[4:]
    links = get_ref_links()
    for c, label, clicks, created in links:
        if c == code:
            ref_link = f"https://t.me/{BOT_USERNAME}?start={code}"
            text = f"📊 *Статистика*\n\n📌 {label}\n🔗 `{ref_link}`\n👥 {clicks}\n📅 {created}"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🗑 Удалить", callback_data=f"del_{code}"))
            markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="ref_list"))
            bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
            bot.delete_message(call.message.chat.id, call.message.message_id)
            return

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
def delete_ref(call):
    if call.from_user.id != ADMIN_ID:
        return
    code = call.data[4:]
    delete_ref_link(code)
    bot.answer_callback_query(call.id, "✅ Удалено!")
    bot.edit_message_text("🗑 Удалено", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_ref")
def back_to_ref(call):
    if call.from_user.id != ADMIN_ID:
        return
    bot.delete_message(call.message.chat.id, call.message.message_id)
    ref_cmd(call.message)

if __name__ == '__main__':
    print("🎬 Кино бот запущен!")
    bot.infinity_polling()
