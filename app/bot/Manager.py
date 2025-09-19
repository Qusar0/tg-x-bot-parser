from aiogram.utils.media_group import MediaGroupBuilder
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
    async def send_photo(chat_id: int, photo: str, text: str, reply_markup=None):
        try:
            await bot.send_photo(chat_id, photo, caption=text, reply_markup=reply_markup)
        except Exception as ex:
            logger.error(ex)

    @staticmethod
    async def send_media_group(chat_id: int, photos: str, text: str):
        media_group = MediaGroupBuilder(caption=text)
        for photo in photos:
            media_group.add_photo(photo)

        try:
            await bot.send_media_group(chat_id, media=media_group.build())
        except Exception as ex:
            logger.error(ex)

    @staticmethod
    async def send_message_to_central_chats(text: str, reply_markup=None):
        for central_chat in settings.get_central_chats():
            await BotManager.send_message(central_chat.chat_id, text, reply_markup)
