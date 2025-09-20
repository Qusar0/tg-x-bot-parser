import asyncio
import aiohttp
from aiogram.utils.media_group import MediaGroupBuilder
from loguru import logger
from app.bot.loader import bot
from app.helpers import check_valid_photo
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
        async with aiohttp.ClientSession() as session:
            if not await check_valid_photo(session, photo):
                logger.warning(f"Поврежденная фотография: {photo}")
                await bot.send_message(chat_id, text, reply_markup=reply_markup)
                return
        try:
            await bot.send_photo(chat_id, photo, caption=text, reply_markup=reply_markup)
        except Exception as ex:
            logger.error(
                f"An error {ex} occurred when sending photo to {chat_id=}"
            )

    @staticmethod
    async def send_media_group(chat_id: int, photos: list[str], text: str, reply_markup=None):
        async with aiohttp.ClientSession() as session:
            tasks = [check_valid_photo(session, photo) for photo in photos]
            photos_resp = await asyncio.gather(*tasks)
            valid_photos = [photo for photo, valid in zip(photos, photos_resp) if valid]

        if not valid_photos:
            await bot.send_message(chat_id, text, reply_markup=reply_markup)
            logger.warning(f"Невозможно отправить поврежденные фотографии: {photos}")
            return

        media_group = MediaGroupBuilder(caption=text)

        for photo in photos:
            media_group.add_photo(photo)

        try:
            await bot.send_media_group(chat_id, media=media_group.build())
        except Exception as ex:
            logger.error(
                f"An error {ex} occurred when sending media group to {chat_id=}"
            )

    @staticmethod
    async def send_message_to_central_chats(text: str, reply_markup=None):
        for central_chat in settings.get_central_chats():
            await BotManager.send_message(central_chat.chat_id, text, reply_markup)
