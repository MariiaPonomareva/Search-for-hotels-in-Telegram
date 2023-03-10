import os
import re

import requests
from telebot.types import Message
from loguru import logger
from dotenv import load_dotenv
from config_data.config import X_RAPIDAPI_KEY

from database.bot_database import User

load_dotenv()


def exact_location(data: dict, loc_id: str) -> tuple[str, str]:
    """
     gets the id of location and returns locations name from data

    :param data: dict Message
    :param loc_id: location id
    :return: location name
    """
    for loc in data['reply_markup']['inline_keyboard']:
        if loc[0]['callback_data'] == loc_id:
            return loc[0]['text'], loc_id[4:]


def delete_tags(html_text):
    text = re.sub('<([^<>]*)>', '', html_text)
    return text


def request_locations(msg):
    url = "https://hotels4.p.rapidapi.com/locations/search"
    curr_user = User.select().where(User.id == msg.from_user.id).get()

    querystring = {
        "query": msg.text.strip(),
        "locale": curr_user.locale,
    }

    headers = {
        'x-rapidapi-key': X_RAPIDAPI_KEY,
        'x-rapidapi-host': "hotels4.p.rapidapi.com"
    }
    logger.info(f'Parameters for search locations: {querystring}')

    try:
        response = requests.request("GET", url, headers=headers, params=querystring, timeout=20)
        if response.status_code == requests.codes.ok:
            data = response.json()
        else:
            print(response.status_code) #заменить на логирование
        logger.info(f'Hotels api(locations) response received: {data}')

        if data.get('message'):
            logger.error(f'Problems with subscription to hotels api {data}')
            raise requests.exceptions.RequestException
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f'Server error: {e}')
    except Exception as e:
        logger.error(f'Error: {e}')


def make_locations_list(msg: Message) -> dict:
    """
    gets data from hotel api response and generate dict: location name - location id
    :param msg: Message
    :return: dict: location name - location id
    """
    data = request_locations(msg)
    if not data:
        return {'bad_request': 'bad_request'}

    try:
        locations = dict()
        if len(data.get('suggestions')[0].get('entities')) > 0:
            for item in data.get('suggestions')[0].get('entities'):
                location_name = delete_tags(item['caption'])
                locations[location_name] = item['destinationId']
            logger.info(locations)
            return locations
    except Exception as e:
        logger.error(f'Could not parse hotel api response. {e}')
