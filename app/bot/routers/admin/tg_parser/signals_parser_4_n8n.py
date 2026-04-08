from __future__ import annotations

import mimetypes
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any

from loguru import logger
from pyrogram import Client
from pyrogram.errors import UsernameNotOccupied, PeerIdInvalid, FloodWait

from app.config import config


@dataclass
class ChannelMedia:
    filename: str
    mime_type: str
    content: bytes

    def size(self) -> int:
        return len(self.content)


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
    has_video: bool
    has_document: bool

    media_type: str | None
    media: ChannelMedia | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.media:
            data["media"] = {
                "filename": self.media.filename,
                "mime_type": self.media.mime_type,
                "size": self.media.size(),
            }
        return data

    def __repr__(self):
        return f"\n\t{{'message_id': {self.message_id}, 'date': {self.date}, 'chat_id': {self.chat_id}, 'chat_title': {self.chat_title}, 'chat_username': {self.chat_username}, 'text': \"... ...\", 'caption': \"... ...\", 'has_photo': {self.has_photo}, 'has_document': {self.has_document}, 'has_video': {self.has_video}, 'media_type': {self.media_type}, 'media': {self.media}}}"


class ChannelHistoryParser:
    def __init__(self) -> None:
        self._client: Client | None = None

    @property
    def session_name(self) -> str:
        return "userbot_pyrogram"

    def _build_client(self) -> Client:
        proxy = {
            "scheme": "http",
            "hostname": "130.254.41.43",
            "port": 6663,
            "username": "user239081",
            "password": "6iogl9",
        }

        return Client(
            name=self.session_name,
            api_id=config.userbot.api_id,
            api_hash=config.userbot.api_hash,
            phone_number=config.userbot.phone_number,
            workdir=".",
            proxy=proxy,
            no_updates=True
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

        client = self._client
        self._client = None

        try:
            await client.stop()
        except OSError as ex:
            logger.warning("Pyrogram stop завершился с сетевым исключением: {}", ex)

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
    def _detect_media_type(message) -> str | None:
        '''
        Настраиваю обнаружение только фотографий
        '''
        if message.photo:
            return "photo"
        # if message.video:
        #     return "video"
        # if message.document:
        #     return "document"
        return None

    async def _download_media_in_memory(self, message) -> ChannelMedia | None:
        media_type = self._detect_media_type(message)
        if media_type is None:
            return None

        file_obj = await self._client.download_media(message, in_memory=True)
        if file_obj is None:
            return None

        content = file_obj.getvalue() if hasattr(file_obj, "getvalue") else bytes(file_obj.getbuffer())

        filename = getattr(file_obj, "name", None) or f"{message.chat.id}_{message.id}"
        mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

        return ChannelMedia(
            filename=filename,
            mime_type=mime_type,
            content=content,
        )

    def _message_to_post(self, message, media) -> ChannelPost:
        return ChannelPost(
            message_id=message.id,
            date=message.date.isoformat() if isinstance(message.date, datetime) else None,
            chat_id=message.chat.id if message.chat else None,
            chat_title=message.chat.title if message.chat else None,
            chat_username=message.chat.username if message.chat else None,
            text=message.text,
            caption=message.caption,
            has_photo=message.photo is not None,
            has_video=message.video is not None,
            has_document=message.document is not None,
            media_type=self._detect_media_type(message),
            media=media,
        )

    async def get_last_posts(
        self,
        channel: str,
        limit: int = 20,
        load_media_binary: bool = False,
    ) -> list[ChannelPost]:
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
        posts: list[ChannelPost] = []

        try:
            async for message in self._client.get_chat_history(normalized_channel, limit=limit):
                media = None
                if load_media_binary:
                    media = await self._download_media_in_memory(message)

                posts.append(self._message_to_post(message, media))

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