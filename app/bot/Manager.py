import asyncio
import aiohttp
from aiogram.utils.media_group import MediaGroupBuilder
from loguru import logger
from app.bot.loader import bot
from app.helpers import check_valid_photo
from app.settings import settings
from aiogram.types import FSInputFile
import os


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
    async def send_photo_from_userbot(chat_id: int, userbot_client, message, text: str, reply_markup=None):
        """Отправка фото из userbot в бот"""
        try:
            if message.photo:
                photo_path = await userbot_client.download_media(message.photo.file_id)

                photo_file = FSInputFile(photo_path)
                await bot.send_photo(chat_id, photo_file, caption=text, reply_markup=reply_markup)

                import os
                os.remove(photo_path)
            else:
                await bot.send_message(chat_id, text, reply_markup=reply_markup)
        except Exception as ex:
            logger.error(f"An error {ex} occurred when sending photo from userbot to {chat_id=}")
            await bot.send_message(chat_id, text, reply_markup=reply_markup)

    @staticmethod
    async def send_media_group_from_userbot(chat_id: int, userbot_client, source_chat_id: int, media_group_id: str, text: str, reply_markup=None):
        """Отправка группы медиа из userbot в бот"""
        try:
            messages = []
            async for msg in userbot_client.get_chat_history(source_chat_id, limit=10):
                if hasattr(msg, 'media_group_id') and str(msg.media_group_id) == media_group_id:
                    messages.append(msg)
                if len(messages) >= 10:  # Ограничиваем количество
                    break

            if not messages:
                await bot.send_message(chat_id, text, reply_markup=reply_markup)
                return

            photo_paths = []
            for msg in messages:
                if msg.photo:
                    photo_path = await userbot_client.download_media(msg.photo.file_id)
                    photo_paths.append(photo_path)

            if not photo_paths:
                await bot.send_message(chat_id, text, reply_markup=reply_markup)
                return

            media_group = MediaGroupBuilder(caption=text)
            for photo_path in photo_paths:
                photo_file = FSInputFile(photo_path)
                media_group.add_photo(photo_file)

            await bot.send_media_group(chat_id, media=media_group.build())

            for photo_path in photo_paths:
                os.remove(photo_path)

        except Exception as ex:
            logger.error(f"An error {ex} occurred when sending media group from userbot to {chat_id=}")
            await bot.send_message(chat_id, text, reply_markup=reply_markup)

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
