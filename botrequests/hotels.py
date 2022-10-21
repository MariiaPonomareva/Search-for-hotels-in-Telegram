import os

import requests
from dotenv import load_dotenv
from loguru import logger
from datetime import datetime
from telebot.types import Message
from config_data.config import X_RAPIDAPI_KEY

from utils.handling import hotel_price, _, hotel_address, \
    hotel_rating, request_photos
from database.bot_database import User, SearchHistory

load_dotenv()


def get_hotels(msg: Message, parameters: dict) -> [list, None]:
    """
    calls the required functions to take and process the hotel data
    :param msg: Message
    :param parameters: search parameters
    :return: list with string like hotel descriptions
    """
    data = request_hotels(parameters, msg)
    if 'bad_req' in data:
        return ['bad_request']
    data = structure_hotels_info(msg, data, parameters)
    if not data or len(data['results']) < 1:
        return None
    if parameters['order'] == 'DISTANCE_FROM_LANDMARK':
        next_page = data.get('next_page')
        distance = float(parameters['distance'])
        while next_page and next_page < 5 \
                and float(data['results'][-1]['distance'].replace(',', '.').split()[0]) <= distance:
            add_data = request_hotels(parameters, next_page)
            if 'bad_req' in data:
                logger.warning('bad_request')
                break
            add_data = structure_hotels_info(msg, add_data, parameters)
            if add_data and len(add_data["results"]) > 0:
                data['results'].extend(add_data['results'])
                next_page = add_data['next_page']
            else:
                break
        quantity = int(parameters['quantity'])
        data = choose_best_hotels(data['results'], distance, quantity)
    else:
        data = data['results']

    data, history_msg = generate_hotels_descriptions(data, msg)

    if parameters['order'] == 'PRICE':
        order = _('lowprice', msg)
    elif parameters['order'] == 'PRICE_HIGHEST_FIRST':
        order = _('highprice', msg)
    else:
        order = _('bestdeal', msg)
    history = (f"{order}\n\n"
               f"{_('search_date', msg)}: {datetime.today()}\n\n"
               f"{_('hotels_list', msg)}:\n" +
               '\n'.join(history_msg) + '\n'
               )
    curr_history = SearchHistory.select().where(SearchHistory.user_id == msg.from_user.id).get()
    curr_history_lst = curr_history.history.split(';')
    if len(curr_history_lst) >= 3:
        del curr_history_lst[0]
    curr_history_lst.append(history)
    curr_history.history = ";".join(curr_history_lst)
    curr_history.save()
    return data


def request_hotels(parameters: dict, page: int = 1):
    """
    request information from the hotel api
    :param parameters: search parameters
    :param page: page number
    :return: response from hotel api
    """
    logger.info(f'Function {request_hotels.__name__} called with argument: page = {page}, parameters = {parameters}')
    url = "https://hotels4.p.rapidapi.com/properties/list"

    querystring = {
        "adults1": "1",
        "pageNumber": page,
        "destinationId": parameters['destination_id'],
        "pageSize": parameters['quantity'],
        "checkIn": parameters['check_in'],
        "checkOut": parameters['check_out'],
        "sortOrder": parameters['order'],
        "locale": parameters['locale'],
        "currency": parameters['currency'],
    }
    if parameters['order'] == 'DISTANCE_FROM_LANDMARK':
        querystring['priceMax'] = parameters['priceMax']
        querystring['priceMin'] = parameters['priceMin']
        querystring['pageSize'] = '25'

    logger.info(f'Search parameters: {querystring}')

    headers = {
        'x-rapidapi-key': X_RAPIDAPI_KEY,
        'x-rapidapi-host': "hotels4.p.rapidapi.com"
    }

    try:
        response = requests.request("GET", url, headers=headers, params=querystring, timeout=20)
        data = response.json()
        if data.get('message'):
            raise requests.exceptions.RequestException

        logger.info(f'Hotels api(properties/list) response received: {data}')
        return data

    except requests.exceptions.RequestException as e:
        logger.error(f'Error receiving response: {e}')
        return {'bad_req': 'bad_req'}
    except Exception as e:
        logger.info(f'Error in function {request_hotels.__name__}: {e}')
        return {'bad_req': 'bad_req'}


def structure_hotels_info(msg: Message, data: dict, parameters: dict) -> dict:
    """
    structures hotel data
    :param msg: Message
    :param data: hotel data
    :param parameters: dict
    :return: dict of structured hotel data
    """
    logger.info(f'Function {structure_hotels_info.__name__} called with argument: msd = {msg}, data = {data}')
    data = data.get('data', {}).get('body', {}).get('searchResults')
    hotels = dict()
    hotels['total_count'] = data.get('totalCount', 0)

    logger.info(f"Next page: {data.get('pagination', {}).get('nextPageNumber', 0)}")
    hotels['next_page'] = data.get('pagination', {}).get('nextPageNumber')
    hotels['results'] = []
    curr_user = User.select().where(User.id == msg.from_user.id).get()

    try:
        if hotels['total_count'] > 0:
            for cur_hotel in data.get('results'):
                hotel = dict()
                hotel['id'] = cur_hotel.get('id')
                hotel['name'] = cur_hotel.get('name')
                hotel['star_rating'] = cur_hotel.get('starRating', 0)
                hotel['price'] = hotel_price(cur_hotel)
                hotel['total_nights'] = parameters['total_nights']
                hotel['total_price'] = round(parameters['total_nights'] * hotel['price'], 2)
                if not hotel['price']:
                    continue
                hotel['distance'] = cur_hotel.get('landmarks')[0].get('distance', _('no_information', msg))
                hotel['address'] = hotel_address(cur_hotel, msg)
                if curr_user.photo_amt > 0:
                    hotel['photos'] = request_photos(cur_hotel, curr_user.photo_amt)

                if hotel not in hotels['results']:
                    hotels['results'].append(hotel)
        logger.info(f'Hotels in function {structure_hotels_info.__name__}: {hotels}')
        return hotels

    except Exception as e:
        logger.info(f'Error in function {structure_hotels_info.__name__}: {e}')


def choose_best_hotels(hotels: list[dict], distance: float, limit: int) -> list[dict]:
    """
    deletes hotels that have a greater distance from the city center than the specified one, sorts the rest by price
    in order increasing and limiting the selection
    :param limit: number of hotels
    :param distance: maximum distance from city center
    :param hotels: structured hotels data
    :return: required number of best hotels
    """
    logger.info(f'Function {choose_best_hotels.__name__} called with arguments: '
                f'distance = {distance}, quantity = {limit}\n{hotels}')
    hotels = list(filter(lambda x: float(x["distance"].strip().replace(',', '.').split()[0]) <= distance, hotels))
    logger.info(f'Hotels filtered: {hotels}')
    hotels = sorted(hotels, key=lambda k: k["price"])
    logger.info(f'Hotels sorted: {hotels}')
    if len(hotels) > limit:
        hotels = hotels[:limit]
    return hotels


def generate_hotels_descriptions(hotels: dict, msg: Message) -> tuple[list, list]:
    """
    generate hotels description
    :param msg: Message
    :param hotels: Hotels information
    :return: list with hotel descriptions and list with information for saving in search history
    """
    logger.info(f'Function {generate_hotels_descriptions.__name__} called with argument {hotels}')
    curr_user = User.select().where(User.id == msg.from_user.id).get()
    hotels_info = []
    request_list = []

    for hotel in hotels:
        message = (
            f"{_('hotel', msg)}: {hotel.get('name')}\n"
            f"{_('rating', msg)}: {hotel_rating(hotel.get('star_rating'), msg)}\n"
            f"{_('price', msg)}: {hotel['price']} {curr_user.currency}\n"
            f"{_('total_nights', msg)}: {hotel['total_nights']}\n"
            f"{_('total_price', msg)}: {hotel['total_price']} {curr_user.currency}\n"
            f"{_('distance', msg)}: {hotel.get('distance')}\n"
            f"{_('address', msg)}: {hotel.get('address')}\n"
        )
        history_message = (
            f"{_('hotel', msg)}: {hotel.get('name')}\n"
            f"{_('price', msg)}: {hotel['price']} {curr_user.currency}\n"
            f"{_('address', msg)}: {hotel.get('address')}\n"
            f"{_('site', msg)}: 'URL:' https://hotels.com/ho{hotel['id']}\n"
        )
        if hotel.get('photos'):
            hotels_info.append({'photos': hotel.get('photos'), 'message': message})
        else:
            hotels_info.append({'message': message})

        request_list.append(history_message)

    return hotels_info, request_list
