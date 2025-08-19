from loguru import logger
from app.bot.loader import bot, dispatcher
from app.bot.middlewares import setup_middlewares
from app.bot.filters import setup_admin_filters
from app.bot.routers import root_handlers_router
from app.bot.commands import set_my_commands


@dispatcher.startup()
async def on_startup():
    me = await bot.get_me()
    await set_my_commands(bot)
    logger.success(f"Бот запущен: @{me.username} | {me.full_name}")


def import_routers():
    import app.bot.routers.admin.open_menu.handlers
    import app.bot.routers.admin.words.handlers
    import app.bot.routers.admin.chats.handlers  # noqa: F401


async def run_bot():
    # Инициализация middlewares
    setup_middlewares(dispatcher)

    # Инициализация фильтров для админа
    setup_admin_filters(dispatcher)

    # Подключение маршрутов
    dispatcher.include_router(root_handlers_router)
    import_routers()

    # Запуск обработчика событий
    used_update_types = dispatcher.resolve_used_update_types()
    await dispatcher.start_polling(bot, allowed_updates=used_update_types)
