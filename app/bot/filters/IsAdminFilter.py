from aiogram import types
from aiogram.filters.base import Filter
from app.config import config
from app.settings import settings


class IsAdminFilter(Filter):
    async def __call__(self, event: types.TelegramObject):
        admins = config.bot.admins + settings.get_admins()
        is_admin = event.from_user.id in admins
        return is_admin
