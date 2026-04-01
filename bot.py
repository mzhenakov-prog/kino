import asyncio
import aiohttp
import ssl
import certifi
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

API_TOKEN = '8381032154:AAEQdqCbxcGOuzunPWhPZbXaCjzaPpJbuhM'
TMDB_API_KEY = 'fdc70aa152320f85d8acdfda64b69b36'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

async def get_movie_info(movie_name):
    url = "https://api.themoviedb.org/3/search/movie"
    params = {
        'api_key': TMDB_API_KEY,
        'query': movie_name,
        'language': 'ru-RU'
    }
    
    # Настройка SSL для обхода блокировок хостинга
    ssl_context = ssl.create_default_context(cafile=certifi.where())

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, ssl=ssl_context) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('results'):
                        movie = data['results'][0]
                        return {
                            'title': movie.get('title'),
                            'overview': movie.get('overview', 'Без описания.'),
                            'rating': movie.get('vote_average', 0),
                            'id': movie.get('id'),
                            'poster': movie.get('poster_path')
                        }
                print(f"Ошибка хостинга: статус {response.status}")
    except Exception as e:
        print(f"Ошибка запроса: {e}")
    return None

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("🔍 Введите название фильма!")

@dp.message()
async def search_movie(message: types.Message):
    # Убираем лишние пробелы в поиске
    query = message.text.strip()
    if not query: return

    movie = await get_movie_info(query)
    
    if movie:
        link = f"https://www.themoviedb.org/movie/{movie['id']}"
        kb = [[types.InlineKeyboardButton(text="🎬 Смотреть фильм", url=link)]]
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
        
        caption = (
            f"🍿 <b>{movie['title']}</b>\n\n"
            f"⭐️ Рейтинг: {movie['rating']}\n\n"
            f"📝 {movie['overview'][:600]}..."
        )
        
        if movie['poster']:
            poster_url = f"https://image.tmdb.org/t/p/w500{movie['poster']}"
            await message.answer_photo(photo=poster_url, caption=caption, reply_markup=keyboard, parse_mode="HTML")
        else:
            await message.answer(caption, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer("❌ Фильм не найден в базе TMDB.")

async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
