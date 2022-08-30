from telebot.types import Message
import keyboards
from loader import bot


@bot.message_handler(commands=['start'])
def bot_start(message: Message):
    bot.reply_to(message, f"Добро пожаловать, {message.from_user.full_name}! "
                          f"Вас приветствует бот агентства Too Easy Travel. Чем я могу Вам помочь?")
    bot.send_message(message.from_user.id, 'Выберите раздел из кнопок ниже:', reply_markup=keyboards.reply.my_menu.start_buttons)




