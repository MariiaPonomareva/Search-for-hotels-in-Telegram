from telebot.types import ReplyKeyboardMarkup, KeyboardButton

start_buttons = ReplyKeyboardMarkup(True, True)
start_buttons.add(KeyboardButton('/lowprice'))
start_buttons.add(KeyboardButton('/cancel'))
