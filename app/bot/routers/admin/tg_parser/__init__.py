# Telegram Parser Module
from aiogram import Router

# Создаем пустой роутер для совместимости
router = Router()

# Импортируем все обработчики
from . import handlers  # noqa
