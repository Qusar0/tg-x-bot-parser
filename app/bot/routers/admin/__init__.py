from app.bot.utils.Router import Router

admin_router = Router()

# Подключаем роутеры
from . import chats
from . import words
from . import tg_parser
from . import x_parser
from . import x_channels

admin_router.include_router(chats.router)
admin_router.include_router(words.router)
admin_router.include_router(tg_parser.router)
admin_router.include_router(x_parser.router)
admin_router.include_router(x_channels.router)