from aiogram import Dispatcher
from .IsAdminFilter import IsAdminFilter
from .ChatType import ChatTypeFilter


def setup_admin_filters(dispatcher: Dispatcher):
    dispatcher.message.filter(ChatTypeFilter("private"))
    dispatcher.message.filter(IsAdminFilter())
