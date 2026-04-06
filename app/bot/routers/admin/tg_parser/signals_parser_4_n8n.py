from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any

from loguru import logger
from pyrogram import Client
from pyrogram.errors import UsernameNotOccupied, PeerIdInvalid, FloodWait

from app.config import config


@dataclass
class ChannelPost:
    message_id: int
    date: str | None
    chat_id: int | None
    chat_title: str | None
    chat_username: str | None
    text: str | None
    caption: str | None
    has_photo: bool
    has_document: bool
    has_video: bool
    media_group_id: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ChannelHistoryParser:
    def __init__(self) -> None:
        self._client: Client | None = None

    @property
    def session_name(self) -> str:
        # Используем уже существующий session-файл userbot_pyrogram.session
        return "userbot_pyrogram"

    def _build_client(self) -> Client:
        return Client(
            name=self.session_name,
            api_id=config.userbot.api_id,
            api_hash=config.userbot.api_hash,
            phone_number=config.userbot.phone_number,
            workdir=".",
        )

    async def start(self) -> None:
        if self._client is not None:
            return

        self._client = self._build_client()
        await self._client.start()
        logger.info("Клиент pyrogram userbot запущен")

    async def stop(self) -> None:
        if self._client is None:
            return

        await self._client.stop()
        self._client = None
        logger.info("Клиент pyrogram userbot остановлен")

    async def __aenter__(self) -> "ChannelHistoryParser":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.stop()

    @staticmethod
    def _normalize_channel(channel: str) -> str:
        channel = channel.strip()

        if channel.startswith("https://t.me/"):
            channel = channel.removeprefix("https://t.me/")
        elif channel.startswith("http://t.me/"):
            channel = channel.removeprefix("http://t.me/")

        if channel.startswith("@"):
            channel = channel[1:]

        return channel.strip("/")

    @staticmethod
    def _message_to_post(message) -> ChannelPost:
        return ChannelPost(
            message_id=message.id,
            date=message.date.isoformat() if isinstance(message.date, datetime) else None,
            chat_id=message.chat.id if message.chat else None,
            chat_title=message.chat.title if message.chat else None,
            chat_username=message.chat.username if message.chat else None,
            text=message.text,
            caption=message.caption,
            has_photo=message.photo is not None,
            has_document=message.document is not None,
            has_video=message.video is not None,
            media_group_id=str(message.media_group_id) if message.media_group_id else None,
        )

    async def get_last_posts(self, channel: str, limit: int = 50) -> list[dict[str, Any]]:
        if limit <= 0:
            raise ValueError("limit must be > 0")

        if self._client is None:
            raise RuntimeError("Client is not started")

        normalized_channel = self._normalize_channel(channel)
        logger.info(
            "Парсинг канала | channel={} | limit={}",
            normalized_channel,
            limit,
        )

        posts: list[dict[str, Any]] = []

        try:
            async for message in self._client.get_chat_history(normalized_channel, limit=limit):
                # Пропускаем служебные пустые сообщения
                if not any([message.text, message.caption, message.photo, message.document, message.video]):
                    continue

                posts.append(self._message_to_post(message).to_dict())

        except UsernameNotOccupied as ex:
            raise ValueError(f"Channel @{normalized_channel} does not exist") from ex
        except PeerIdInvalid as ex:
            raise ValueError(
                f"Cannot access channel @{normalized_channel}. "
                f"It may be private or unavailable for this account"
            ) from ex
        except FloodWait as ex:
            raise RuntimeError(f"Telegram FloodWait: wait {ex.value} seconds") from ex

        logger.info(
            "Парсинг канала завершён успешно | channel={} | posts_count={}",
            normalized_channel,
            len(posts),
        )

        return posts