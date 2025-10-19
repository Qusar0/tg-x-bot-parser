import os
import contextlib
from loguru import logger
from pyrogram import Client, filters, idle, enums, types
from pyrogram.handlers import MessageHandler
from pyrogram.errors import UserAlreadyParticipant, UserBot
from app.userbot.handlers import Handlers
from app.config import config
from app.database.repo.Chat import ChatRepo


class UserbotManager:
    def __init__(self, api_id: int, api_hash: str, phone_number: str):
        self.client = Client(
            "../userbot_pyrogram",
            api_id=api_id,
            api_hash=api_hash,
            phone_number=phone_number,
            parse_mode=enums.ParseMode.HTML,
        )

    async def start(self):
        logger.info("Запускаем userbot...")
        self.client.add_handler(MessageHandler(Handlers.message_handler, filters.incoming))
        logger.info("Обработчик сообщений добавлен")
        await self.client.start()
        logger.success("Юзербот запущен!")
        logger.info("Userbot готов к получению сообщений")
        await idle()
        await self.client.stop()

    async def stop(self):
        await self.client.stop()

    async def get_chat(self, chat_id: int | str):
        try:
            chat = await self.client.get_chat(chat_id)
            return chat
        except Exception as ex:
            logger.error(ex)
            return None

    async def join_chat(self, chat_id: int | str):
        chat = await self.client.join_chat(chat_id)
        return chat

    async def add_member(self, chat_id: int | str, user_id: int | str) -> bool:
        with contextlib.suppress(UserAlreadyParticipant):
            try:
                await self.client.add_chat_members(chat_id, user_id)
            except UserBot:
                await self.client.promote_chat_member(chat_id, user_id)

        return True

    async def leave_chat(self, chat_id: str | int) -> bool:
        await self.client.leave_chat(chat_id)
        return True

    async def get_dialogs(self, is_only_groups: bool = False) -> list[types.Chat]:
        "Нужно ли возвращать чат или нужно диалог"

        if os.environ["APP_MODE"] == "dev":
            return []

        dialogs = []
        central_chats = await ChatRepo.get_central_chats()
        central_chats_ids = [central.telegram_id for central in central_chats]

        async for dialog in self.client.get_dialogs():
            if is_only_groups:
                if dialog.chat and dialog.chat.type in [
                    enums.ChatType.GROUP,
                    enums.ChatType.CHANNEL,
                    enums.ChatType.SUPERGROUP,
                    enums.ChatType.GROUP.value,
                    enums.ChatType.CHANNEL.value,
                    enums.ChatType.SUPERGROUP.value,
                ]:
                    if getattr(dialog.chat, 'id', None) not in central_chats_ids:
                        dialogs.append(dialog.chat)
            else:
                dialogs.append(dialog.chat)

        return dialogs


userbot_manager = UserbotManager(
    config.userbot.api_id,
    config.userbot.api_hash,
    config.userbot.phone_number,
)
