from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


start_buttons = InlineKeyboardMarkup()
start_buttons.add(InlineKeyboardButton(text='Поиск самых дешевых отелей', callback_data='lowprice'))

date_buttons = InlineKeyboardMarkup()

