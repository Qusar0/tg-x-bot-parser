import time

from aiogram import types
from aiogram.filters import Command
from loguru import logger

from app.bot.routers.admin import admin_router
from app.database.repo.Chat import ChatRepo
from app.settings import settings
from app.userbot import poller_state
from app.userbot.channel_status import (
    build_channels_status_messages,
    get_stale_after_sec,
    load_channels_status_data,
)
from app.userbot.userbot_manager import userbot_manager


@admin_router.message(Command("channels_status"))
async def channels_status_handler(message: types.Message):
    """Показывает администраторам состояние всех Telegram-каналов мониторинга."""
    try:
        chats = await ChatRepo.get_monitoring_chats()
        channels = await load_channels_status_data(chats, poller_state)
        stale_after_sec = get_stale_after_sec(settings.get_poller_interval_sec())
        userbot_connected = bool(
            getattr(userbot_manager.client, "is_connected", False)
        )

        report_messages = build_channels_status_messages(
            channels,
            now=time.time(),
            stale_after_sec=stale_after_sec,
            poller_enabled=settings.get_poller_enabled(),
            userbot_connected=userbot_connected,
        )
        for report in report_messages:
            await message.answer(report)
    except Exception:
        logger.exception("Ошибка формирования отчёта /channels_status")
        await message.answer(
            "❌ Не удалось получить статус каналов. Подробности записаны в лог."
        )
