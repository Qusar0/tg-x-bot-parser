from app.bot.utils.Router import Router
from app.bot.routers.admin import admin_router

# Импортируем все роутеры для регистрации
import app.bot.routers.admin.open_menu.handlers  # noqa
import app.bot.routers.admin.chats.handlers  # noqa
import app.bot.routers.admin.words.handlers  # noqa
import app.bot.routers.admin.tg_parser.handlers.menu  # noqa
import app.bot.routers.admin.x_parser.handlers.menu  # noqa

root_handlers_router = Router()
root_handlers_router.include_router(admin_router)
