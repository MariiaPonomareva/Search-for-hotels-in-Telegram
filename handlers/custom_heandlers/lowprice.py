from keyboards.reply.contact import request_contact
from telebot.types import Message
from loader import bot
from states.search import UserSearchState


@bot.message_handler(commands=['lowprice'])
def lowprice(message: Message) -> None:
    bot.send_message(message.from_user.id, 'Выбран поиск по самым дешевым отелям')
    bot.send_message(message.from_user.id, 'Введите название города:')
    bot.set_state(message.from_user.id, UserSearchState.city, message.chat.id)

