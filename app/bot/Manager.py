import asyncio
import aiohttp
from aiogram.utils.media_group import MediaGroupBuilder
from loguru import logger
from app.bot.loader import bot
from app.helpers import check_valid_photo
from app.database.repo.Chat import ChatRepo
from aiogram.types import FSInputFile
from aiogram.types.input_file import BufferedInputFile
import os


class BotManager:
    @staticmethod
    async def send_message(chat_id: int, text: str, reply_markup=None):
        try:
            logger.info(f"Отправляем сообщение в чат {chat_id}, текст: {text[:50]}...")
            await bot.send_message(chat_id, text, reply_markup=reply_markup)
            logger.success(f"Сообщение успешно отправлено в чат {chat_id}")
        except Exception as ex:
            logger.error(f"Ошибка отправки в чат {chat_id}: {ex}")

    @staticmethod
    async def send_photo(chat_id: int, photo: str, text: str, reply_markup=None):
        try:
            await bot.send_photo(chat_id, photo, caption=text, reply_markup=reply_markup)
            return
        except TelegramBadRequest as e:
            # Ошибка Telegram API (например, бот не админ, неверный чат и т.п.)
            logger.error(f"BadRequest при отправке фото в чат {chat_id}: {e}")
            return  # чтобы не падал парсер
        except TelegramForbiddenError as e:
            # Бот заблокирован / удалён из чата
            logger.error(f"Forbidden при отправке фото в чат {chat_id}: {e}")
            return
        except Exception as ex:
            logger.warning(f"Direct URL send failed, fallback to download. Error: {ex}")

    # Фоллбэк: скачиваем и отправляем как файл
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(photo, allow_redirects=True) as resp:
                    if 200 <= resp.status < 400:
                        content = await resp.read()
                        content_type = resp.headers.get("Content-Type", "image/jpeg")
                        ext = ".jpg"
                        if "png" in content_type:
                            ext = ".png"
                        elif "webp" in content_type:
                            ext = ".webp"
                        file = BufferedInputFile(content, filename=f"photo{ext}")
                        await bot.send_photo(chat_id, file, caption=text, reply_markup=reply_markup)
                        return
        except Exception as ex:
        # Ошибка скачивания или отправки файла
            logger.error(f"Fallback download send failed for chat_id={chat_id}, url={photo}. Error: {ex}")

    # В крайнем случае — просто текст, без фото
        try:
            await bot.send_message(chat_id, text, reply_markup=reply_markup)
        except Exception as ex:
            logger.error(f"Ошибка отправки текстового fallback-сообщения в чат {chat_id}: {ex}")

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
    async def send_media_group_from_userbot(chat_id: int,
                                            userbot_client,
                                            source_chat_id: int,
                                            media_group_id: str,
                                            text: str,
                                            reply_markup=None
                                            ):
        """Отправка группы медиа из userbot в бот"""
        try:
            messages = []
            async for msg in userbot_client.get_chat_history(source_chat_id, limit=10):
                if hasattr(msg, 'media_group_id') and str(msg.media_group_id) == media_group_id:
                    messages.append(msg)
                if len(messages) >= 10:
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
        # Попытка отправить по URL напрямую
        media_group = MediaGroupBuilder(caption=text)
        for photo in photos:
            media_group.add_photo(photo)
        try:
            await bot.send_media_group(chat_id, media=media_group.build())
            return
        except Exception as ex:
            logger.warning(f"Direct media group send failed, fallback to download. Error: {ex}")

        # Фоллбэк: скачиваем сами и отправляем как файлы
        try:
            files: list[BufferedInputFile] = []
            async with aiohttp.ClientSession() as session:
                for photo in photos:
                    try:
                        async with session.get(photo, allow_redirects=True) as resp:
                            if 200 <= resp.status < 400:
                                content = await resp.read()
                                content_type = resp.headers.get("Content-Type", "image/jpeg")
                                ext = ".jpg"
                                if "png" in content_type:
                                    ext = ".png"
                                elif "webp" in content_type:
                                    ext = ".webp"
                                files.append(BufferedInputFile(content, filename=f"photo{ext}"))
                    except Exception:
                        continue

            if not files:
                await bot.send_message(chat_id, text, reply_markup=reply_markup)
                logger.warning(f"Невозможно отправить фотографии (fallback пуст): {photos}")
                return

            media_group = MediaGroupBuilder(caption=text)
            for f in files:
                media_group.add_photo(f)
            await bot.send_media_group(chat_id, media=media_group.build())
        except Exception as ex:
            logger.error(f"Fallback media group send failed for {chat_id=}. Error: {ex}")
            await bot.send_message(chat_id, text, reply_markup=reply_markup)

    @staticmethod
    async def send_message_to_central_chats(text: str, reply_markup=None):
        for central_chat in await ChatRepo.get_central_chats():
            await BotManager.send_message(central_chat.telegram_id, text, reply_markup)