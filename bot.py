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
KINOPOISK_API_KEY = 'bdb7430d-d2f2-49cd-a884-744df1085261'

bot = telebot.TeleBot(BOT_TOKEN)
KINOPOISK_URL = 'https://kinopoiskapiunofficial.tech/api'

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

# ========== ПОИСК ФИЛЬМОВ ==========
def search_movies(query, limit=10):
    """Поиск фильмов через Kinopoisk Unofficial API"""
    try:
        headers = {'X-API-KEY': KINOPOISK_API_KEY}
        params = {'keyword': query, 'page': 1}
        url = f"{KINOPOISK_URL}/v2.1/films/search-by-keyword"
        r = requests.get(url, headers=headers, params=params, timeout=10)
        data = r.json()
        
        movies = []
        for item in data.get('films', [])[:limit]:
            movies.append({
                'id': item.get('filmId'),
                'name': item.get('nameRu') or item.get('nameEn', 'Без названия'),
                'year': item.get('year', '—'),
                'rating': item.get('rating', 0),
                'description': item.get('description', 'Описание отсутствует'),
                'poster': item.get('posterUrl'),
                'genres': [g['genre'] for g in item.get('genres', [])][:3]
            })
        return movies
    except Exception as e:
        print(f"Ошибка поиска: {e}")
        return []

def get_movie_by_id(movie_id):
    """Получить фильм по ID"""
    try:
        headers = {'X-API-KEY': KINOPOISK_API_KEY}
        url = f"{KINOPOISK_URL}/v2.2/films/{movie_id}"
        r = requests.get(url, headers=headers, timeout=10)
        return r.json()
    except:
        return None

def get_top_movies():
    """Топ-250 фильмов"""
    try:
        headers = {'X-API-KEY': KINOPOISK_API_KEY}
        params = {'type': 'TOP_250_BEST', 'page': 1}
        url = f"{KINOPOISK_URL}/v2.2/films/top"
        r = requests.get(url, headers=headers, params=params, timeout=10)
        data = r.json()
        
        movies = []
        for item in data.get('films', [])[:10]:
            movies.append({
                'id': item.get('filmId'),
                'name': item.get('nameRu') or item.get('nameEn', 'Без названия'),
                'year': item.get('year', '—'),
                'rating': item.get('rating', 0),
                'poster': item.get('posterUrl')
            })
        return movies
    except:
        return []

def get_premieres():
    """Премьеры текущего года"""
    try:
        headers = {'X-API-KEY': KINOPOISK_API_KEY}
        params = {'year': datetime.now().year, 'month': 'APRIL'}
        url = f"{KINOPOISK_URL}/v2.2/films/premieres"
        r = requests.get(url, headers=headers, params=params, timeout=10)
        data = r.json()
        
        movies = []
        for item in data.get('items', [])[:10]:
            movies.append({
                'id': item.get('filmId'),
                'name': item.get('nameRu') or item.get('nameEn', 'Без названия'),
                'year': item.get('year', '—'),
                'rating': item.get('rating', 0),
                'poster': item.get('posterUrl')
            })
        return movies
    except:
        return []

# ========== КНОПКИ ==========
def main_menu(is_admin=False):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔍 Поиск фильмов", "🏆 Топ 250")
    markup.add("🎬 Премьеры", "⭐ Популярное")
    if is_admin:
        markup.add("🔗 Рефералка")
    markup.add("❓ Помощь")
    return markup

def ref_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("➕ Создать ссылку", callback_data="ref_create"))
    markup.add(types.InlineKeyboardButton("📊 Мои ссылки", callback_data="ref_list"))
    return markup

def movie_buttons(movies, page=0, per_page=5):
    start = page * per_page
    end = min(start + per_page, len(movies))
    page_movies = movies[start:end]
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for movie in page_movies:
        name = movie['name'][:40]
        year = movie['year'] if movie['year'] else '—'
        rating = f"⭐ {movie['rating']}" if movie.get('rating') else ''
        markup.add(types.InlineKeyboardButton(f"🎬 {name} ({year}) {rating}", callback_data=f"movie_{movie['id']}"))
    
    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"movies_page_{page-1}"))
    if end < len(movies):
        nav.append(types.InlineKeyboardButton("➡️ Далее", callback_data=f"movies_page_{page+1}"))
    if nav:
        markup.add(*nav)
    
    return markup, page_movies

# ========== ДАННЫЕ ==========
user_data = {}

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
    welcome = """🎥 *КИНО БОТ* | Фильмы | Сериалы

Найди любой фильм или сериал!

*Возможности:*
🔍 Поиск фильмов
🏆 Топ 250 лучших
🎬 Премьеры
⭐ Популярное

По вопросам: @avgustc"""
    
    bot.send_message(message.chat.id, welcome, reply_markup=main_menu(is_admin), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🔍 Поиск фильмов")
def search_cmd(message):
    bot.send_message(message.chat.id, "🔍 *Введи название фильма*", parse_mode='Markdown')
    bot.register_next_step_handler(message, do_search)

def do_search(message):
    wait = bot.send_message(message.chat.id, "🔎 *Ищу...*", parse_mode='Markdown')
    movies = search_movies(message.text, limit=20)
    bot.delete_message(message.chat.id, wait.message_id)
    
    if not movies:
        bot.send_message(message.chat.id, "❌ Ничего не найдено.")
        return
    
    user_data[message.chat.id] = {'movies': movies, 'query': message.text}
    markup, _ = movie_buttons(movies, 0)
    bot.send_message(message.chat.id, f"🎬 *Результаты:* {message.text}", reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🏆 Топ 250")
def top_cmd(message):
    wait = bot.send_message(message.chat.id, "🔎 *Загружаю топ...*", parse_mode='Markdown')
    movies = get_top_movies()
    bot.delete_message(message.chat.id, wait.message_id)
    
    if movies:
        user_data[message.chat.id] = {'movies': movies, 'query': "🏆 Топ 250"}
        markup, _ = movie_buttons(movies, 0)
        bot.send_message(message.chat.id, "🏆 *Топ 250 лучших фильмов*", reply_markup=markup, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "❌ Не удалось загрузить топ.")

@bot.message_handler(func=lambda m: m.text == "🎬 Премьеры")
def premiere_cmd(message):
    wait = bot.send_message(message.chat.id, "🔎 *Загружаю премьеры...*", parse_mode='Markdown')
    movies = get_premieres()
    bot.delete_message(message.chat.id, wait.message_id)
    
    if movies:
        user_data[message.chat.id] = {'movies': movies, 'query': "🎬 Премьеры"}
        markup, _ = movie_buttons(movies, 0)
        bot.send_message(message.chat.id, "🎬 *Скоро в прокате*", reply_markup=markup, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "❌ Не удалось загрузить премьеры.")

@bot.message_handler(func=lambda m: m.text == "⭐ Популярное")
def popular_cmd(message):
    wait = bot.send_message(message.chat.id, "🔎 *Загружаю популярное...*", parse_mode='Markdown')
    movies = get_top_movies()
    bot.delete_message(message.chat.id, wait.message_id)
    
    if movies:
        user_data[message.chat.id] = {'movies': movies, 'query': "⭐ Популярное"}
        markup, _ = movie_buttons(movies, 0)
        bot.send_message(message.chat.id, "⭐ *Популярные фильмы*", reply_markup=markup, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "❌ Не удалось загрузить.")

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

🔍 Поиск фильмов
🏆 Топ 250
🎬 Премьеры
⭐ Популярное

@avgustc"""
    if is_admin:
        help_text += "\n\n🔗 Рефералка"
    bot.send_message(message.chat.id, help_text, reply_markup=main_menu(is_admin), parse_mode='Markdown')

# ========== CALLBACK ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('movies_page_'))
def handle_movies_page(call):
    page = int(call.data.split('_')[2])
    data = user_data.get(call.message.chat.id)
    if not data:
        bot.answer_callback_query(call.id, "❌ Устарело")
        return
    movies = data['movies']
    markup, _ = movie_buttons(movies, page)
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('movie_'))
def show_movie(call):
    movie_id = int(call.data.split('_')[1])
    bot.answer_callback_query(call.id, "📽 Загружаю...")
    
    movie = get_movie_by_id(movie_id)
    if not movie:
        bot.send_message(call.message.chat.id, "❌ Ошибка")
        return
    
    name = movie.get('nameRu') or movie.get('nameEn', 'Без названия')
    year = movie.get('year', '—')
    rating = movie.get('ratingKinopoisk', 0)
    description = movie.get('description', 'Описание отсутствует')
    genres = ', '.join([g['genre'] for g in movie.get('genres', [])])
    poster = movie.get('posterUrl')
    
    text = f"🎬 *{name}* ({year})\n⭐ {rating}/10\n🎭 {genres}\n\n📖 {description[:500]}..."
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Назад к списку", callback_data="back_to_list"))
    
    if poster:
        bot.send_photo(call.message.chat.id, poster, caption=text, reply_markup=markup, parse_mode='Markdown')
    else:
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "back_to_list")
def back_to_list(call):
    data = user_data.get(call.message.chat.id)
    if not data:
        bot.answer_callback_query(call.id, "❌ Устарело")
        return
    movies = data['movies']
    markup, _ = movie_buttons(movies, 0)
    bot.edit_message_text(f"🎬 *Результаты:* {data['query']}", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')

# ========== РЕФЕРАЛЬНЫЕ КНОПКИ ==========
@bot.callback_query_handler(func=lambda call: call.data == "ref_create")
def create_ref(call):
    if call.from_user.id != ADMIN_ID:
        return
    msg = bot.send_message(call.message.chat.id, "📝 *Введи название для ссылки*", parse_mode='Markdown')
    bot.register_next_step_handler(msg, save_ref)

def save_ref(message):
    label = message.text.strip()
    code = f"ref_{int(time.time())}"
    add_ref_link(code, label)
    ref_link = f"https://t.me/{BOT_USERNAME}?start={code}"
    bot.send_message(message.chat.id, f"✅ *Ссылка создана!*\n\n🔗 `{ref_link}`\n📌 {label}", parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "ref_list")
def list_refs(call):
    if call.from_user.id != ADMIN_ID:
        return
    links = get_ref_links()
    if not links:
        bot.send_message(call.message.chat.id, "📭 *Нет созданных ссылок*", parse_mode='Markdown')
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
            text = f"📊 *Статистика ссылки*\n\n📌 {label}\n🔗 `{ref_link}`\n👥 Переходов: {clicks}\n📅 Создана: {created}"
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
    bot.answer_callback_query(call.id, "✅ Ссылка удалена!")
    bot.edit_message_text("🗑 Ссылка удалена", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_ref")
def back_to_ref(call):
    if call.from_user.id != ADMIN_ID:
        return
    bot.delete_message(call.message.chat.id, call.message.message_id)
    ref_cmd(call.message)

if __name__ == '__main__':
    print("🎬 Кино бот запущен!")
    bot.infinity_polling()
