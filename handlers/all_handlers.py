import os

import telebot
from telegram_bot_calendar import DetailedTelegramCalendar
from loader import bot
from telebot.types import Message, CallbackQuery
from dotenv import load_dotenv
from loguru import logger
from datetime import date

from botrequests.hotels import get_hotels
from botrequests.locations import exact_location, make_locations_list
from utils.handling import internationalize as _, is_input_correct, get_parameters_information, \
    make_message, steps, locales, logger_config, currencies, is_user_in_db, add_user, extract_search_parameters, \
    check_in_date, check_out_date
from database.bot_database import User, SearchHistory

logger.configure(**logger_config)
load_dotenv()


def get_locations(msg: Message) -> None:
    """
    takes location name, searches locations with similar name and sends result to chat
    :param msg: Message
    :return: None
    """
    if not is_input_correct(msg):
        bot.send_message(msg.chat.id, make_message(msg, 'mistake_'))
    else:
        wait_msg = bot.send_message(msg.chat.id, _('wait', msg))
        locations = make_locations_list(msg)
        bot.delete_message(msg.chat.id, wait_msg.id)
        if not locations or len(locations) < 1:
            bot.send_message(msg.chat.id, str(msg.text) + _('locations_not_found', msg))
        elif locations.get('bad_request'):
            bot.send_message(msg.chat.id, _('bad_request', msg))
        else:
            menu = telebot.types.InlineKeyboardMarkup()
            for loc_name, loc_id in locations.items():
                menu.add(telebot.types.InlineKeyboardButton(
                    text=loc_name,
                    callback_data='code' + loc_id)
                )
            menu.add(telebot.types.InlineKeyboardButton(text=_('cancel', msg), callback_data='cancel'))
            bot.send_message(msg.chat.id, _('loc_choose', msg), reply_markup=menu)


@bot.message_handler(commands=['settings'])
def get_command_settings(message: Message) -> None:
    """
    "/settings" command handler, opens settings menu
    :param message: Message
    :return: None
    """
    if not is_user_in_db(message):
        add_user(message)
    logger.info(f'Функция {get_command_settings.__name__} вызвана с параметром: {message}')
    menu = telebot.types.InlineKeyboardMarkup()
    menu.add(telebot.types.InlineKeyboardButton(text=_("language_", message), callback_data='set_locale'))
    menu.add(telebot.types.InlineKeyboardButton(text=_("currency_", message), callback_data='set_currency'))
    menu.add(telebot.types.InlineKeyboardButton(text=_("cancel", message), callback_data='cancel'))
    bot.send_message(message.chat.id, _("settings", message), reply_markup=menu)


@bot.message_handler(commands=['lowprice', 'highprice', 'bestdeal'])
def get_searching_commands(message: Message) -> None:
    """
    "/lowprice", "/highprice", "/bestdeal"  commands handler, sets the sort order and starts asking for parameters
    from the user

    :param message: Message
    :return: None
    """
    logger.info("\n" + "=" * 100 + "\n")
    if not is_user_in_db(message):
        add_user(message)
    chat_id = message.chat.id
    curr_user = User.select().where(User.id == message.from_user.id).get()
    curr_user.state = 1
    curr_user.save()
    if 'lowprice' in message.text:
        curr_user.order = 'PRICE'
        curr_user.save()
        logger.info('"lowprice" command is called')
    elif 'highprice' in message.text:
        curr_user.order = 'PRICE_HIGHEST_FIRST'
        curr_user.save()
        logger.info('"highprice" command is called')
    else:
        curr_user.order = 'DISTANCE_FROM_LANDMARK'
        curr_user.save()
        logger.info('"bestdeal" command is called')
    logger.info(curr_user.order)
    state = curr_user.state
    logger.info(f"Current state: {state}")
    bot.send_message(chat_id, make_message(message, 'question_'))


@bot.message_handler(commands=['help', 'start'])
def get_command_help(message: Message) -> None:
    """
    "/help" command handler, displays information about bot commands in the chat
    :param message: Message
    :return: None
    """
    if not is_user_in_db(message):
        add_user(message)
    if 'start' in message.text:
        logger.info(f'"start" command is called')
        bot.send_message(message.chat.id, _('hello', message))
    else:
        logger.info(f'"help" command is called')
        bot.send_message(message.chat.id, _('help', message))


@bot.message_handler(commands=['history'])
def get_history(message: Message) -> None:
    """
    "/history" command handler, displays information about the last 3 requests from user
    :param message: Message
    :return: None
    """
    if not is_user_in_db(message):
        add_user(message)
    logger.info(f'"history" command is called')

    curr_history = SearchHistory.select().where(SearchHistory.user_id == message.from_user.id).get()
    if curr_history.history == ';':
        bot.send_message(message.chat.id, _('no_history', message))
    else:
        bot.send_message(message.chat.id, curr_history.history.replace(';', ''))


@bot.callback_query_handler(func=DetailedTelegramCalendar.func())
def cal(c: CallbackQuery) -> None:
    """
    calendar buttons handler
    :param c: CallbackQuery
    :return: None
    """
    curr_user = User.select().where(User.id == c.from_user.id).get()
    for k, v in locales.items():
        if curr_user.locale == v:
            locale = k
            break
        else:
            locale = 'en'
    state = curr_user.state
    result, key, step = DetailedTelegramCalendar(locale=locale, min_date=date.today()).process(c.data)
    if not result and key:
        bot.edit_message_text(_('choose', c),
                              c.message.chat.id,
                              c.message.message_id,
                              reply_markup=key)
    elif result:
        bot.edit_message_text(_('chosen', c) + f" {result}",
                              c.message.chat.id,
                              c.message.message_id)
        if state == 5:
            curr_user.check_in = result
            curr_user.state = 6
            curr_user.save()
            check_out_date(c)

        elif state == 6:
            curr_user.check_out = result
            curr_user.state = 0
            curr_user.save()

            yes_no = telebot.types.InlineKeyboardMarkup()
            yes_no.add(telebot.types.InlineKeyboardButton(text=_("yes", c), callback_data='yes'))
            yes_no.add(telebot.types.InlineKeyboardButton(text=_("no", c), callback_data='no'))
            bot.send_message(c.message.chat.id, _('need_photo', c), reply_markup=yes_no)


@bot.callback_query_handler(func=lambda call: True)
def keyboard_handler(call: CallbackQuery) -> None:
    """
    buttons handlers
    :param call: CallbackQuery
    :return: None
    """
    logger.info(f'Function {keyboard_handler.__name__} called with argument: {call}')
    chat_id = call.message.chat.id
    bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id)
    curr_user = User.select().where(User.id == call.from_user.id).get()

    if call.data.startswith('code'):
        if curr_user.state != 1:
            bot.send_message(call.message.chat.id, _('enter_command', call))
            curr_user.state = 0
            curr_user.save()
        else:
            loc_name, loc_id = exact_location(call.message.json, call.data)
            curr_user.dest_id = loc_id
            curr_user.destination_name = loc_name
            curr_user.save()
            logger.info(f"{loc_name} selected")
            bot.send_message(
                chat_id,
                f"{_('loc_selected', call)}: {loc_name}",
            )
            if curr_user.order == 'DISTANCE_FROM_LANDMARK':
                curr_user.state = 2
                curr_user.save()
            else:
                curr_user.state += 3
                curr_user.save()
            bot.send_message(chat_id, make_message(call, 'question_'))

    elif call.data.startswith('set'):
        curr_user.state = 0
        curr_user.save()
        menu = telebot.types.InlineKeyboardMarkup()
        if call.data == 'set_locale':
            logger.info(f'language change menu')
            menu.add(telebot.types.InlineKeyboardButton(text='Русский', callback_data='loc_ru_RU'))
            menu.add(telebot.types.InlineKeyboardButton(text='English', callback_data='loc_en_US'))
        elif call.data == 'set_currency':
            logger.info(f'currency change menu')
            menu.add(telebot.types.InlineKeyboardButton(text='RUB', callback_data='cur_RUB'))
            menu.add(telebot.types.InlineKeyboardButton(text='USD', callback_data='cur_USD'))
            menu.add(telebot.types.InlineKeyboardButton(text='EUR', callback_data='cur_EUR'))
        menu.add(telebot.types.InlineKeyboardButton(text=_('cancel', call), callback_data='cancel'))
        bot.send_message(chat_id, _('ask_to_select', call), reply_markup=menu)
    elif call.data == 'yes':
        curr_user.state = 7
        curr_user.save()
        bot.send_message(call.message.chat.id, _('photo_amt', call))
    elif call.data == 'no':
        curr_user.photo_amt = 0
        curr_user.save()
        hotels_list(call)

    elif call.data.startswith('loc'):
        curr_user.locale = call.data[4:]
        curr_user.language = call.data[4:6]
        curr_user.save()
        bot.send_message(chat_id, f"{_('current_language', call)}: {_('language', call)}")
        logger.info(f"Language changed to {curr_user.language}")
        logger.info(f"Locale changed to {curr_user.locale}")

    elif call.data.startswith('cur'):
        curr_user.currency = call.data[4:]
        curr_user.save()
        bot.send_message(chat_id, f"{_('current_currency', call)}: {call.data[4:]}")
        logger.info(f"Currency changed to {curr_user.currency}")

    elif call.data == 'cancel':
        logger.info(f'Canceled by user')
        curr_user.state = 0
        curr_user.save()
        bot.send_message(chat_id, _('canceled', call))


def get_search_parameters(msg: Message) -> None:
    """
    fixes search parameters
    :param msg: Message
    :return: None
    """
    logger.info(f'Function {get_search_parameters.__name__} called with argument: {msg}')
    chat_id = msg.chat.id
    curr_user = User.select().where(User.id == msg.from_user.id).get()
    state = curr_user.state
    if not is_input_correct(msg):
        bot.send_message(chat_id, make_message(msg, 'mistake_'))
    else:
        if state == 2:
            min_price, max_price = sorted(msg.text.strip().split(), key=int)
            curr_user.min_price = min_price
            curr_user.save()
            logger.info(f"{steps[str(state) + 'min']} set to {min_price}")
            curr_user.max_price = max_price
            curr_user.save()
            logger.info(f"{steps[str(state) + 'max']} set to {max_price}")
            curr_user.state = 3
            curr_user.save()
            bot.send_message(chat_id, make_message(msg, 'question_'))
        elif state == 4:
            curr_user.quantity = msg.text.strip()
            curr_user.state = 5
            curr_user.save()
            logger.info(f"{steps[str(state)]} set to {msg.text.strip()}")
            check_in_date(msg)
        elif state == 7:
            curr_user.photo_amt = msg.text.strip()
            curr_user.state = 0
            curr_user.save()
            logger.info(f"{steps[str(state)]} set to {msg.text.strip()}")
            hotels_list(msg)
        else:
            curr_user.distance = msg.text.strip()
            curr_user.state = 4
            curr_user.save()
            logger.info(f"{steps[str(state)]} set to {msg.text.strip()}")
            bot.send_message(chat_id, make_message(msg, 'question_'))


def hotels_list(msg: Message, lang: str = None) -> None:
    """
    displays hotel search results in chat
    :param msg: Message
    :param lang: str
    :return: None
    """
    curr_user = User.select().where(User.id == msg.from_user.id).get()
    chat_id = msg.from_user.id
    wait_msg = bot.send_message(chat_id, _('wait', msg))
    params = extract_search_parameters(msg)
    hotels = get_hotels(msg, params)
    logger.info(f'Function {get_hotels.__name__} returned: {hotels}')
    bot.delete_message(chat_id, wait_msg.id)
    if not hotels or len(hotels) < 1:
        bot.send_message(chat_id, _('hotels_not_found', msg))
    elif 'bad_request' in hotels:
        bot.send_message(chat_id, _('bad_request', msg))
    else:
        quantity = len(hotels)
        bot.send_message(chat_id, get_parameters_information(msg), lang)
        bot.send_message(chat_id, f"{_('hotels_found', msg)}: {quantity}")
        for hotel in hotels:
            if hotel.get('photos'):
                for i_photo in hotel['photos']:
                    bot.send_photo(chat_id, photo=i_photo, parse_mode='html')
            bot.send_message(chat_id, hotel['message'], lang)
    curr_user.photo_amt = 0
    curr_user.save()


@bot.message_handler(content_types=['text'])
def get_text_messages(message: Message) -> None:
    """
    text messages handler
    :param message: Message
    :return: None
    """
    if not is_user_in_db(message):
        add_user(message)
    curr_user = User.select().where(User.id == message.from_user.id).get()
    state = str(curr_user.state)
    if state == '1':
        get_locations(message)
    elif state in ['2', '3', '4', '5', '7']:
        get_search_parameters(message)
    else:
        bot.send_message(message.chat.id, _('misunderstanding', message))



