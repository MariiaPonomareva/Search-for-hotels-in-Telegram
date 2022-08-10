from telebot.handler_backends import State, StatesGroup


class UserSearchState(StatesGroup):
    city = State()
