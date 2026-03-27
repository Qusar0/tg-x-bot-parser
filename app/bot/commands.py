from aiogram import types
from app.bot.utils.Bot import Bot


async def set_my_commands(bot: Bot):
    await bot.set_my_commands(
        [
            types.BotCommand(command="/start", description="🦍 Открыть главное меню"),
            types.BotCommand(command="check", description="Проверить канал"),
            # types.BotCommand(command="/keywords", description="Настроить ключ-слова"),
            # types.BotCommand(command="/stopwords", description="Настроить стоп-слова"),
            # types.BotCommand(command="/blacklist", description="Черный список"),
        ]
    )
