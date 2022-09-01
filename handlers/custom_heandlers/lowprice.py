import datetime

from telebot.types import Message, CallbackQuery
from loader import bot
from states.search import UserSearchState
import requests
import re
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP


def city_founding(my_city):
    url = "https://hotels4.p.rapidapi.com/locations/v2/search"
    querystring = {"query": f"{my_city}"}
    headers = {
        "X-RapidAPI-Key": "cbc2ecdbafmsh7d3c15ef7de51bcp137a0ejsn3e863b9fe03a",
        "X-RapidAPI-Host": "hotels4.p.rapidapi.com"
    }
    response = requests.request("GET", url, headers=headers, params=querystring)
    pattern = r'(?<="CITY_GROUP",).+?[\]]'
    find = re.search(pattern, response.text)
    if find:
        suggestions = json.loads(f"{{{find[0]}}}")

        cities = list()
        for dest_id in suggestions['entities']:
            clear_destination = dest_id['name']
            cities.append({'city_name': clear_destination,
                           'destination_id': dest_id['destinationId']
                           }
                          )
        return cities
    else:
        return None


def city_markup(my_city):
    cities = city_founding(my_city)
    destinations = InlineKeyboardMarkup()
    if cities is not None:
        for city in cities:
            destinations.add(InlineKeyboardButton(text=city['city_name'],
                                                  callback_data=f'{city["destination_id"]}'))
        return destinations
    else:
        return None


@bot.message_handler(commands=['lowprice'])
def lowprice(message: Message) -> None:
    bot.send_message(message.from_user.id, 'Выбран поиск по самым дешевым отелям.\nВ каком городе ищем?')
    bot.register_next_step_handler(message, city)
    bot.set_state(message.from_user.id, UserSearchState.city)


def city(message):
    bot.send_message(message.from_user.id, 'Уточните, пожалуйста:', reply_markup=city_markup(message.text))


@bot.callback_query_handler(func=lambda call: call.data.isdigit())
def get_city(call) -> None:
    with bot.retrieve_data(user_id=call.from_user.id) as data:
        data['city_id'] = call.text
        #bot.answer_callback_query(callback_query.id)
    calendar, step = DetailedTelegramCalendar(min_date=datetime.date.today()).build()
    bot.send_message(call.from_user.id, f'Теперь выберите дату заезда: {LSTEP[step]}', reply_markup=calendar)
    bot.set_state(call.from_user.id, UserSearchState.start_date, call.chat.id)


@bot.callback_query_handler(DetailedTelegramCalendar().func())
def get_start_date(call):
    result, key, step = DetailedTelegramCalendar().process(call.data)
    if not result and key:
        bot.edit_message_text(f"Select {LSTEP[step]}",
                              call.message.chat.id,
                              call.message.message_id,
                              reply_markup=key)
    elif result:
        bot.edit_message_text(f"Вы выбрали: {result}",
                              call.message.chat.id,
                              call.message.message_id)

    with bot.retrieve_data(user_id=call.from_user.id) as data:
        data['start_date'] = result.text
    bot.set_state(call.from_user.id, UserSearchState.end_date, call.chat.id)

