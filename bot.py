import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Твои данные, которые ты предоставил
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
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data['results']:
                        # Берем самый релевантный (первый) результат
                        movie = data['results'][0]
                        return {
                            'title': movie.get('title'),
                            'overview': movie.get('overview', 'Описание пока не завезли.'),
                            'rating': movie.get('vote_average', 0),
                            'id': movie.get('id'),
                            'poster': movie.get('poster_path')
                        }
    except Exception as e:
        print(f"Ошибка при запросе к API: {e}")
    return None

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("🎬 **Бот по поиску фильмов готов к работе!**\n\nПросто напиши название фильма, и я найду информацию о нем.")

@dp.message()
async def search_movie(message: types.Message):
    movie = await get_movie_info(message.text)
    
    if movie:
        # Формируем ссылку на страницу фильма
        # Можно заменить на любой другой сервис, подставив название
        link = f"https://www.themoviedb.org/movie/{movie['id']}"
        
        # Создаем кнопку-ссылку
        kb = [[types.InlineKeyboardButton(text="🔗 Смотреть фильм", url=link)]]
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
        
        # Формируем текст сообщения
        caption = (
            f"🍿 <b>{movie['title']}</b>\n\n"
            f"⭐️ <b>Рейтинг:</b> {movie['rating']}/10\n\n"
            f"📝 <b>Описание:</b>\n{movie['overview'][:600]}..." 
        )
        
        # Если есть постер, отправляем с картинкой
        if movie['poster']:
            poster_url = f"https://image.tmdb.org/t/p/w500{movie['poster']}"
            await message.answer_photo(photo=poster_url, caption=caption, reply_markup=keyboard, parse_mode="HTML")
        else:
            await message.answer(caption, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer("🔍 Ничего не нашлось. Попробуй уточнить название.")

async def main():
    print("Бот успешно запущен и ждет сообщений...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен")
