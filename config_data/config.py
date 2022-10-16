import os
from dotenv import load_dotenv, find_dotenv

if not find_dotenv():
    exit('Переменные окружения не загружены т.к отсутствует файл .env')
else:
    load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
DEFAULT_COMMANDS = (
    ('help', "справка"),
    ('lowprice', "поиск по наименьшей цене"),
    ('highprice', "поиск по наибольшей цене"),
    ('bestdeal', "лучшее предложение"),
    ('history', "история поиска"),
    ('settings', "настройки")
)
