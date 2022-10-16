import re
from datetime import datetime, timedelta, date

import requests
from telegram_bot_calendar import DetailedTelegramCalendar

from telebot.types import Message
from loguru import logger
from loader import bot

from database.bot_database import User, SearchHistory
from translations.translations import vocabulary

steps = {
    '1': 'destination_id',
    '2min': 'min_price',
    '2max': 'max_price',
    '3': 'distance',
    '4': 'quantity',
    '5': 'check_in_date',
    '6': 'check_out_date',
    '7': 'photo_amt'
}
currencies = {
    "ru": "RUB",
    "en": "USD"
}
locales = {
    "ru": "ru_RU",
    "en": "en_US"
}

logger_config = {
    "handlers": [
        {
            "sink": "logs/bot.log",
            "format": "{time} | {level} | {message}",
            "encoding": "utf-8",
            "level": "DEBUG",
            "rotation": "5 MB",
            "compression": "zip"
        },
    ],
}


def internationalize(key: str, msg: Message) -> str:
    """
    takes text in vocabulary in current language with key
    :param key: str key
    :param msg: Message
    :return: text of message from vocabulary
    """
    curr_user = User.select().where(User.id == msg.from_user.id).get()
    lang = curr_user.language
    return vocabulary[key][lang]


_ = internationalize


def is_input_correct(msg: Message) -> bool:
    """
    Checks the correctness of incoming messages as search parameters
    :param msg: Message
    :return: True if the message text is correct
    """
    curr_user = User.select().where(User.id == msg.from_user.id).get()
    state = str(curr_user.state)
    msg = msg.text.strip()
    if state == '7' and msg.isdigit() and int(msg) <= 6:
        return True
    elif state == '5' and msg.replace(' ', '').replace('-', '').isdigit():
        return True
    elif state == '4' and ' ' not in msg and msg.isdigit() and 0 < int(msg) <= 20:
        return True
    elif state == '3' and ' ' not in msg and msg.replace('.', '').isdigit():
        return True
    elif state == '2' and msg.replace(' ', '').isdigit() and len(msg.split()) == 2:
        return True
    elif state == '1' and msg.replace(' ', '').replace('-', '').isalpha():
        return True


def get_parameters_information(msg: Message) -> str:
    """
    generates a message with information about the current search parameters
    :param msg: Message
    :return: string like information about search parameters
    """
    logger.info(f'Function {get_parameters_information.__name__} called with argument: {msg}')
    curr_user = User.select().where(User.id == msg.from_user.id).get()
    parameters = {
        'destination_id': curr_user.dest_id,
        'quantity': curr_user.quantity,
        'order': curr_user.order,
        'locale': curr_user.locale,
        'currency': curr_user.currency,
        'priceMax': curr_user.max_price,
        'priceMin': curr_user.min_price,
        'destination_name': curr_user.destination_name,
        'distance': curr_user.distance,
    }
    sort_order = parameters['order']
    city = parameters['destination_name']
    currency = parameters['currency']
    message = (
        f"{_('parameters', msg)}\n"
        f"{_('city', msg)}: {city}\n"
    )
    if sort_order == "DISTANCE_FROM_LANDMARK":
        price_min = parameters['priceMin']
        price_max = parameters['priceMax']
        distance = parameters['distance']
        message += f"{_('price', msg)}: {price_min} - {price_max} {currency}\n" \
                   f"{_('max_distance', msg)}: {distance} {_('dis_unit', msg)}"
    logger.info(f'Search parameters: {message}')
    return message


def make_message(msg: Message, prefix: str) -> str:
    """
    makes and returns messages with information about an invalid input or with question, depending on the prefix and
    state
    :param msg: Message
    :param prefix: prefix for key in vocabulary dictionary
    :return: string like message
    """
    curr_user = User.select().where(User.id == msg.from_user.id).get()
    state = str(curr_user.state)
    message = _(prefix + state, msg)
    if state == '2':
        message += f" ({curr_user.currency})"

    return message


def hotel_price(hotel: dict) -> int:
    """
    return hotel price
    :param hotel: dict - hotel information
    :return: integer or float like number
    """

    price = 0
    try:
        if hotel.get('ratePlan').get('price').get('exactCurrent'):
            price = hotel.get('ratePlan').get('price').get('exactCurrent')
        else:
            price = hotel.get('ratePlan').get('price').get('current')
            price = int(re.sub(r'[^0-9]', '', price))
    except Exception as e:
        logger.warning(f'Hotel price getting error {e}')

    return price


def hotel_address(hotel: dict, msg: Message) -> str:
    """
    returns hotel address
    :param msg: Message
    :param hotel: dict - hotel information
    :return: hotel address
    """
    message = _('no_information', msg)
    if hotel.get('address'):
        message = hotel.get('address').get('streetAddress', message)
    return message


def hotel_rating(rating: float, msg: Message) -> str:
    """
    returns rating hotel in asterisks view
    :param rating: hotel rating
    :param msg: Message
    :return: string like asterisks view hotel rating
    """
    if not rating:
        return _('no_information', msg)
    return '⭐' * int(rating)


def request_photos(hotel: dict, amt: int) -> list[str]:
    """
        returns list with links to hotel photos
        :param hotel: dict - hotel information
        :param amt: int - Number of photos
        :return: links to hotel photos
        """
    photos_list = None
    if hotel.get('id'):
        url = "https://hotels4.p.rapidapi.com/properties/get-hotel-photos"

        querystring = {"id": hotel.get('id')}

        headers = {
            "X-RapidAPI-Key": "b144609875msh13fbef50261efd2p1d1328jsn2ed7a53d275a",
            "X-RapidAPI-Host": "hotels4.p.rapidapi.com"
        }

        response = requests.request("GET", url, headers=headers, params=querystring)
        data = response.json()
        photos_list = []
        all_photos = data['hotelImages'][:amt]
        for photo in all_photos:
            curr_link = photo['baseUrl'].replace('{size}', 'z')
            if curr_link not in photos_list:
                photos_list.append(curr_link)

    return photos_list


def check_in_date(msg: Message) -> None:
    """
    asks the user to select check in date
    :param msg: Message
    :return: None
    """
    curr_user = User.select().where(User.id == msg.from_user.id).get()
    for k, v in locales.items():
        if curr_user.locale == v:
            locale = k
            break
        else:
            locale = 'en'

    calendar, step = DetailedTelegramCalendar(locale=locale, min_date=date.today()).build()
    bot.send_message(msg.chat.id, _('check_in_date', msg))
    bot.send_message(msg.chat.id, _('choose', msg), reply_markup=calendar)


def check_out_date(msg: Message) -> None:
    """
    asks the user to select check out date
    :param msg: Message
    :return: None
    """
    curr_user = User.select().where(User.id == msg.from_user.id).get()
    for k, v in locales.items():
        if curr_user.locale == v:
            locale = k
            break
        else:
            locale = 'en'
    calendar, step = DetailedTelegramCalendar(locale=locale, min_date=date.today() + timedelta(1)).build()
    bot.send_message(msg.message.chat.id, _('check_out_date', msg))
    bot.send_message(msg.message.chat.id, _('choose', msg), reply_markup=calendar)


def add_user(msg: Message) -> None:
    """
    adds user to database
    :param msg: Message
    :return: None
    """
    logger.info("add_user called")
    user_id = msg.from_user.id
    lang = msg.from_user.language_code
    if lang != 'ru':
        lang = 'en'
    User.create(
        id=user_id,
        username=msg.from_user.username,
        language=lang,
        state=0,
        locale=locales[lang],
        currency=currencies[lang],
        order='start',
        dest_id='0',
        destination_name='0',
        check_in='0',
        check_out='0',
        quantity='0',
        min_price='0',
        max_price='0',
        distance=0,
        photo_amt=0
    )
    SearchHistory.create(
        user_id=user_id,
        history=''
    )


def is_user_in_db(msg: Message) -> bool:
    """
    checks if is user in database
    :param msg: Message
    :return: True if user in database
    """
    logger.info('is_user_in_db called')
    user_id = msg.from_user.id
    try:
        answer = User.get(User.id == user_id)
    except Exception:
        answer = None
    return answer


def extract_search_parameters(msg: Message) -> dict:
    """
    extracts users search parameters from database
    :param msg: Message
    :return: dict with search parameters
    """
    logger.info(f"Function {extract_search_parameters.__name__} called")
    curr_user = User.select().where(User.id == msg.from_user.id).get()
    params = {
        'destination_id': curr_user.dest_id,
        'quantity': curr_user.quantity,
        'order': curr_user.order,
        'locale': curr_user.locale,
        'currency': curr_user.currency,
        'priceMax': curr_user.max_price,
        'priceMin': curr_user.min_price,
        'distance': curr_user.distance,
        'check_in': curr_user.check_in,
        'check_out': curr_user.check_out,
        'total_nights': (datetime.strptime(curr_user.check_out, "%Y-%m-%d") - datetime.strptime(curr_user.check_in, "%Y-%m-%d")).days,
        'photo_amt': curr_user.photo_amt
    }
    logger.info(f"parameters: {params}")
    return params
