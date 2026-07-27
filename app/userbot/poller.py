"""Поллер мониторинг-каналов.

Периодически читает историю каналов через get_chat_history и отдаёт новые
сообщения в существующий обработчик. Нужен там, где push-апдейты Telegram
по каналу не приходят.
"""
import asyncio

from loguru import logger
from pyrogram.errors import FloodWait


class ChannelPoller:
    def __init__(
        self,
        client=None,
        handler=None,
        chats_provider=None,
        state=None,
        sleep=None,
        settings=None,
    ):
        self._client = client
        self._handler = handler
        self._chats_provider = chats_provider
        self._state = state
        self._settings = settings
        self._sleep = sleep or asyncio.sleep

    def _get_client(self):
        if self._client is not None:
            return self._client

        from app.userbot.userbot_manager import userbot_manager

        return userbot_manager.client

    def _get_handler(self):
        if self._handler is not None:
            return self._handler

        from app.userbot.handlers import Handlers

        return Handlers.message_handler

    def _get_state(self):
        if self._state is not None:
            return self._state

        from app.userbot import poller_state

        return poller_state

    def _get_settings(self):
        if self._settings is not None:
            return self._settings

        from app.settings import settings

        return settings

    async def _get_chats(self):
        if self._chats_provider is not None:
            return await self._chats_provider()

        from app.database.repo.Chat import ChatRepo

        return await ChatRepo.get_monitoring_chats()

    async def poll_channel(self, chat_id: int, limit: int) -> int:
        """Читает новые сообщения канала и отдаёт их в обработчик."""
        client = self._get_client()
        state = self._get_state()

        last_id = await state.get_last_id(chat_id)

        if last_id is None:
            newest_id = None
            async for message in client.get_chat_history(chat_id, limit=1):
                newest_id = message.id

            if newest_id is None:
                logger.info(f"Поллер: канал {chat_id} — история пуста, позиция не установлена")
                return 0

            await state.set_last_id(chat_id, newest_id)
            logger.info(
                f"Поллер: канал {chat_id} — первая инициализация, "
                f"стартовая позиция {newest_id}, старые сообщения не отправляем"
            )
            return 0

        new_messages = []
        reached_last = False
        async for message in client.get_chat_history(chat_id, limit=limit):
            if message.id <= last_id:
                reached_last = True
                break
            new_messages.append(message)

        if not new_messages:
            return 0

        if not reached_last and len(new_messages) >= limit:
            logger.warning(
                f"Поллер: канал {chat_id} — выбран лимит {limit} сообщений, "
                f"часть постов могла быть пропущена"
            )

        new_messages.reverse()

        handler = self._get_handler()
        processed = 0
        max_id = last_id

        for message in new_messages:
            max_id = max(max_id, message.id)

            try:
                await handler(client, message)
                processed += 1
            except Exception as ex:
                logger.error(
                    f"Поллер: ошибка обработки сообщения {message.id} канала {chat_id}: {ex}"
                )

        await state.set_last_id(chat_id, max_id)

        if processed:
            logger.info(f"Поллер: канал {chat_id} — обработано новых сообщений: {processed}")

        return processed

    async def poll_once(self) -> int:
        """Один полный обход всех мониторинг-каналов."""
        chats = await self._get_chats()
        config = self._get_settings()
        limit = config.get_poller_limit()
        delay = config.get_poller_channel_delay_sec()

        logger.info(f"Поллер: начинаем обход, каналов: {len(chats)}")

        total = 0
        for chat in chats:
            try:
                total += await self.poll_channel(chat.telegram_id, limit)
            except FloodWait as ex:
                logger.warning(
                    f"Поллер: FloodWait {ex.value} сек на канале {chat.telegram_id}, ждём"
                )
                await self._sleep(ex.value)
            except Exception as ex:
                logger.warning(f"Поллер: канал {chat.telegram_id} недоступен: {ex}")

            await self._sleep(delay)

        logger.info(f"Поллер: обход завершён, обработано сообщений: {total}")
        return total

    async def start(self) -> None:
        """Бесконечный цикл обходов с интервалом из настроек."""
        logger.info("Поллер: запущен")

        while True:
            config = self._get_settings()
            interval = config.get_poller_interval_sec()

            if not config.get_poller_enabled():
                await self._sleep(interval)
                continue

            client = self._get_client()
            if not getattr(client, "is_connected", False):
                logger.info("Поллер: userbot ещё не подключён, ждём следующей итерации")
                await self._sleep(interval)
                continue

            try:
                await self.poll_once()
            except Exception as ex:
                logger.error(f"Поллер: ошибка обхода: {ex}")

            await self._sleep(interval)


channel_poller = ChannelPoller()
