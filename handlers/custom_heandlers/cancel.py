from telebot.types import Message
import keyboards
from loader import bot


@bot.message_handler(commands=['cancel'])
def bot_cancel(message: Message):
    bot.reply_to(message, "Давайте начнем сначала)")
    bot.set_state(message.from_user.id, None)
    bot.send_message(message.from_user.id, 'Выберите раздел из меню:', reply_markup=keyboards.reply.my_menu.start_buttons)