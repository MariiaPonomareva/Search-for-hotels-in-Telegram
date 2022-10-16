from loader import bot
from loguru import logger
import handlers
from telebot.custom_filters import StateFilter
from utils.set_bot_commands import set_default_commands


if __name__ == '__main__':
    bot.add_custom_filter(StateFilter(bot))
    set_default_commands(bot)
    bot.polling(none_stop=True, interval=0)





