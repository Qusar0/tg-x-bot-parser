from loguru import logger
from app.bot.loader import bot
from app.settings import settings


class BotManager:
    @staticmethod
    async def send_message(chat_id: int, text: str, reply_markup=None):
        try:
            await bot.send_message(chat_id, text, reply_markup=reply_markup)
        except Exception as ex:
            logger.error(ex)

    @staticmethod
    async def send_message_to_central_chats(text: str, reply_markup=None):
        for central_chat in settings.get_central_chats():
            await BotManager.send_message(central_chat.chat_id, text, reply_markup)
