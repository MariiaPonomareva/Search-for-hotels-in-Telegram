from telebot.handler_backends import State, StatesGroup


class UserSearchState(StatesGroup):
    city = State()
    start_date = State()
    end_date = State()
