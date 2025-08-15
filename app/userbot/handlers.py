from loguru import logger
from pyrogram import Client, types
from app.database.repo.Chat import ChatRepo
from app.userbot.filters.is_word_match import is_word_match
from app.enums import WordType
from app.bot.Manager import BotManager
from app.helpers import is_duplicate


class Handlers:
    @staticmethod
    async def message_handler(client: Client, message: types.Message):
        if message.service:
            return

        text = message.text or message.caption

        if not text:
            return

        candidate = await ChatRepo.get_by_telegram_id(message.chat.id)
        if not candidate:
            return

        keywords = await is_word_match(text, WordType.keyword)
        if not keywords:
            return

        stopwords = await is_word_match(text, WordType.stopword)
        if stopwords:
            return

        if await is_duplicate(f"{message.chat.id}:{message.id}", text):
            logger.info(f"Поймали дубликат в сообщении: {message.link}")
            return

        logger.info(f"Получили сообщение: {message.link}")

        central_chats = list(set(keyword.central_chat_id for keyword in keywords))
        for central_chat in central_chats:
            await BotManager.send_message(central_chat, text.html)
