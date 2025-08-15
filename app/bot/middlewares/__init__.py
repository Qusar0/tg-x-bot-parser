from aiogram import Dispatcher
from .LogAction import LogActionMiddleware
from .Register import RegisterMiddleware


def setup_middlewares(dispatcher: Dispatcher):
    # Логирование действий
    log_middleware = LogActionMiddleware()
    dispatcher.message.outer_middleware.register(log_middleware)
    dispatcher.callback_query.outer_middleware.register(log_middleware)

    # Создание пользователя в базе данных
    register_user_middlewaare = RegisterMiddleware()
    dispatcher.message.outer_middleware.register(register_user_middlewaare)
    dispatcher.callback_query.outer_middleware.register(register_user_middlewaare)
