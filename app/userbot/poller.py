"""Поллер мониторинг-каналов.

Периодически читает историю каналов через get_chat_history и отдаёт новые
сообщения в существующий обработчик. Нужен там, где push-апдейты Telegram
по каналу не приходят.
"""
import asyncio
import time

from loguru import logger
from pyrogram.errors import FloodWait


class ChannelPoller:
    # Безопасный интервал на случай, если сами настройки не читаются (например,
    # некорректное значение poller_interval_sec в settings.json роняет int(...)
    # внутри геттера ещё до того, как рабочий интервал стал известен).
    DEFAULT_INTERVAL_SEC = 300
    # Нижняя граница интервала: нулевой/отрицательный интервал из настроек даст
    # asyncio.sleep(0/отрицательное) — горячий цикл, выжирающий CPU.
    MIN_INTERVAL_SEC = 30

    def __init__(
        self,
        client=None,
        handler=None,
        chats_provider=None,
        state=None,
        sleep=None,
        settings=None,
        clock=None,
    ):
        self._client = client
        self._handler = handler
        self._chats_provider = chats_provider
        self._state = state
        self._settings = settings
        self._sleep = sleep or asyncio.sleep
        self._clock = clock or time.time

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

    async def _record_channel_health(self, chat_id: int, error: str | None = None) -> None:
        """Сохраняет телеметрию, не влияя на основной цикл доставки."""
        try:
            await self._get_state().set_channel_health(
                chat_id,
                checked_at=self._clock(),
                error=error,
            )
        except Exception as ex:
            logger.warning(
                f"Поллер: не удалось сохранить состояние канала {chat_id}: {ex}"
            )

    async def poll_channel(self, chat_id: int, limit: int, max_age_sec: int | None = None) -> int:
        """Читает новые сообщения канала и отдаёт их в обработчик.

        max_age_sec — порог возраста сообщения в секундах. Сообщения старше порога
        не передаются в обработчик (это защита от вывала бэклога после простоя
        поллера), но позиция (max_id) всё равно уезжает вперёд через них, иначе
        канал застрянет на старом хвосте навсегда. None отключает проверку возраста
        (используется, когда вызывающий код не заботится о возрасте, например в
        существующих тестах, не передающих этот параметр).
        """
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
        now = self._clock()

        for message in new_messages:
            max_id = max(max_id, message.id)

            message_date = getattr(message, "date", None)
            if max_age_sec is not None and message_date is not None:
                age_sec = now - message_date.timestamp()
                if age_sec > max_age_sec:
                    logger.info(
                        f"Поллер: канал {chat_id} — сообщение {message.id} пропущено "
                        f"по возрасту ({age_sec:.0f} сек > {max_age_sec} сек), позиция сдвинута"
                    )
                    continue

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
        max_age_sec = config.get_poller_max_age_sec()

        logger.info(f"Поллер: начинаем обход, каналов: {len(chats)}")

        total = 0
        for chat in chats:
            try:
                total += await self.poll_channel(chat.telegram_id, limit, max_age_sec)
                await self._record_channel_health(chat.telegram_id)
            except FloodWait as ex:
                await self._record_channel_health(
                    chat.telegram_id,
                    error=f"FloodWait: {ex.value} сек",
                )
                logger.warning(
                    f"Поллер: FloodWait {ex.value} сек на канале {chat.telegram_id}, ждём"
                )
                await self._sleep(ex.value)
            except Exception as ex:
                await self._record_channel_health(
                    chat.telegram_id,
                    error=f"{type(ex).__name__}: {ex}",
                )
                logger.warning(f"Поллер: канал {chat.telegram_id} недоступен: {ex}")

            await self._sleep(delay)

        logger.info(f"Поллер: обход завершён, обработано сообщений: {total}")
        return total

    async def start(self) -> None:
        """Бесконечный цикл обходов с интервалом из настроек.

        Тело итерации целиком обёрнуто в try — ошибка в настройках (например,
        нечисловое или отсутствующее значение poller_interval_sec в
        settings.json, из-за которого int(...) в геттере бросает исключение)
        не должна убивать цикл: иначе вместе с поллером в asyncio.gather без
        return_exceptions упадёт весь процесс — и бот, и юзербот. При ошибке
        пауза берётся по безопасному интервалу по умолчанию.
        """
        logger.info("Поллер: запущен")

        while True:
            interval = self.DEFAULT_INTERVAL_SEC
            try:
                config = self._get_settings()
                interval = config.get_poller_interval_sec()

                if interval < self.MIN_INTERVAL_SEC:
                    logger.warning(
                        f"Поллер: интервал {interval} сек некорректен (меньше "
                        f"{self.MIN_INTERVAL_SEC}), используем минимальный"
                    )
                    interval = self.MIN_INTERVAL_SEC

                if not config.get_poller_enabled():
                    logger.info("Поллер: выключен настройкой, ждём следующей итерации")
                else:
                    client = self._get_client()
                    if not getattr(client, "is_connected", False):
                        logger.info("Поллер: userbot ещё не подключён, ждём следующей итерации")
                    else:
                        await self.poll_once()
            except Exception as ex:
                logger.error(f"Поллер: ошибка обхода: {ex}")

            await self._sleep(interval)


channel_poller = ChannelPoller()
