import asyncio
import requests # Попробуем обычный requests для обхода блоков
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

API_TOKEN = '8381032154:AAEQdqCbxcGOuzunPWhPZbXaCjzaPpJbuhM'
TMDB_API_KEY = 'fdc70aa152320f85d8acdfda64b69b36'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

def get_movie_full_info(query):
    # 1. Ищем сам фильм
    search_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={query}&language=ru-RU"
    try:
        response = requests.get(search_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if not data.get('results'):
                return None
            
            movie = data['results'][0]
            movie_id = movie['id']
            
            # 2. Делаем второй запрос, чтобы достать актеров (credits)
            credits_url = f"https://api.themoviedb.org/3/movie/{movie_id}/credits?api_key={TMDB_API_KEY}&language=ru-RU"
            credits_resp = requests.get(credits_url, timeout=10).json()
            
            # Берем первых 5 актеров
            cast = [member['name'] for member in credits_resp.get('cast', [])[:5]]
            cast_str = ", ".join(cast) if cast else "Нет данных"
            
            return {
                'title': movie.get('title'),
                'rating': movie.get('vote_average'),
                'overview': movie.get('overview'),
                'actors': cast_str,
                'poster': movie.get('poster_path'),
                'link': f"https://www.themoviedb.org/movie/{movie_id}"
            }
    except Exception as e:
        print(f"Ошибка: {e}")
    return "Error"

@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("🎬 Напиши название фильма, и я пришлю описание и состав актеров!")

@dp.message()
async def handle_search(m: types.Message):
    info = get_movie_full_info(m.text)
    
    if info == "Error":
        await m.answer("⚠️ Ошибка связи с базой данных. Возможно, хостинг блокирует запрос.")
    elif info:
        text = (
            f"🍿 <b>{info['title']}</b>\n\n"
            f"⭐️ <b>Рейтинг:</b> {info['rating']}\n"
            f"🎭 <b>В ролях:</b> {info['actors']}\n\n"
            f"📝 <b>Описание:</b>\n{info['overview'][:600]}..."
        )
        
        kb = [[types.InlineKeyboardButton(text="🔗 Подробнее на сайте", url=info['link'])]]
        markup = types.InlineKeyboardMarkup(inline_keyboard=kb)
        
        if info['poster']:
            await m.answer_photo(f"https://image.tmdb.org/t/p/w500{info['poster']}", caption=text, reply_markup=markup, parse_mode="HTML")
        else:
            await m.answer(text, reply_markup=markup, parse_mode="HTML")
    else:
        await m.answer("❌ Ничего не найдено.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
