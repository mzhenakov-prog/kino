import telebot
import requests

BOT_TOKEN = '8381032154:AAEQdqCbxcGOuzunPWhPZbXaCjzaPpJbuhM'
TMDB_KEY = 'fdc70aa152320f85d8acdfda64b69b36'

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "Введи название фильма")

@bot.message_handler(func=lambda m: True)
def search(m):
    query = m.text
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_KEY}&query={query}&language=ru-RU"
    
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        
        # Отправляем сырой ответ API в чат
        bot.send_message(m.chat.id, f"API ответил:\n{data}")
        
    except Exception as e:
        bot.send_message(m.chat.id, f"Ошибка: {e}")

if __name__ == '__main__':
    print("Тестовый бот запущен")
    bot.infinity_polling()
