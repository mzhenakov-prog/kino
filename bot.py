import telebot
from telebot import types
import requests

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = '8381032154:AAEQdqCbxcGOuzunPWhPZbXaCjzaPpJbuhM'
TMDB_API_KEY = 'fdc70aa152320f85d8acdfda64b69b36'

bot = telebot.TeleBot(BOT_TOKEN)
TMDB_URL = 'https://api.themoviedb.org/3'
IMAGE_URL = 'https://image.tmdb.org/t/p/w500'

# ========== ПОИСК ФИЛЬМА ==========
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
        
        # Берём первый нормальный фильм
        movie = results[0]
        for item in results:
            if item.get('vote_average', 0) > 0 and 'изучение' not in item.get('title', '').lower():
                movie = item
                break
        
        return {
            'id': movie.get('id'),
            'name': movie.get('title', 'Без названия'),
            'year': movie.get('release_date', '')[:4] if movie.get('release_date') else '—',
            'rating': movie.get('vote_average', 0),
            'description': movie.get('overview', 'Описание отсутствует'),
            'poster': f"{IMAGE_URL}{movie.get('poster_path')}" if movie.get('poster_path') else None
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

def get_stars(rating):
    if rating <= 0:
        return "Нет рейтинга"
    stars = int((rating / 2) + 0.5)
    return '⭐' * stars

# ========== КОМАНДЫ ==========
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🎬 *КИНО БОТ*\n\nВведи название фильма — я покажу описание и рейтинг.", parse_mode='Markdown')

@bot.message_handler(func=lambda m: True)
def handle_message(message):
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
    
    text = f"🎬 *{name}* ({year})\n\n"
    text += f"⭐ *Рейтинг:* {rating}/10 {stars}\n"
    if genres:
        text += f"🎭 *Жанр:* {genres}\n"
    if actors:
        text += f"🎭 *В ролях:* {actors}\n\n"
    text += f"📖 *Описание:*\n{description[:500]}..."
    
    if poster:
        bot.send_photo(message.chat.id, poster, caption=text, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, text, parse_mode='Markdown')

if __name__ == '__main__':
    print("🎬 Кино бот запущен!")
    bot.infinity_polling()
