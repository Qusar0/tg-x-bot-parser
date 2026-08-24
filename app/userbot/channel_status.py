"""Чистая модель отчёта о состоянии Telegram-каналов мониторинга."""

import asyncio
from dataclasses import dataclass
from html import escape

from app.userbot.poller_state import ChannelHealth


REPORT_CHUNK_LIMIT = 3900


def get_stale_after_sec(poller_interval_sec: int) -> int:
    """Возвращает порог устаревания после трёх ожидаемых циклов поллера."""
    return max(int(poller_interval_sec), 30) * 3


@dataclass(frozen=True)
class ChannelStatusData:
    telegram_id: int
    title: str
    entity: str | None
    last_id: int | None
    health: ChannelHealth | None


async def load_channels_status_data(chats: list, state) -> list[ChannelStatusData]:
    async def load_chat(chat) -> ChannelStatusData:
        health, last_id = await asyncio.gather(
            state.get_channel_health(chat.telegram_id),
            state.get_last_id(chat.telegram_id),
        )
        return ChannelStatusData(
            telegram_id=chat.telegram_id,
            title=chat.title,
            entity=chat.entity,
            last_id=last_id,
            health=health,
        )

    return list(await asyncio.gather(*(load_chat(chat) for chat in chats)))


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 1] + "…"


def _format_age(seconds: float) -> str:
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds} сек назад"
    if seconds < 60 * 60:
        return f"{seconds // 60} мин назад"
    if seconds < 24 * 60 * 60:
        return f"{seconds // (60 * 60)} ч назад"
    return f"{seconds // (24 * 60 * 60)} дн назад"


def _status_kind(
    channel: ChannelStatusData,
    *,
    now: float,
    stale_after_sec: int,
) -> str:
    if channel.health is None:
        return "warning"
    if channel.health.error is not None:
        return "error"
    if now - channel.health.checked_at > stale_after_sec:
        return "warning"
    return "ok"


def _format_channel(
    index: int,
    channel: ChannelStatusData,
    *,
    now: float,
    stale_after_sec: int,
) -> tuple[str, str]:
    kind = _status_kind(channel, now=now, stale_after_sec=stale_after_sec)
    icon = {"ok": "✅", "warning": "⚠️", "error": "❌"}[kind]
    title = escape(_truncate(channel.title or str(channel.telegram_id), 120))
    identity = escape(_truncate(channel.entity or str(channel.telegram_id), 120))
    position = channel.last_id if channel.last_id is not None else "нет"
    first_line = f"{index}. {icon} <b>{title}</b> ({identity})"

    if channel.health is None:
        details = (
            "статус: ещё не проверен поллером; "
            f"позиция поллера: {position}"
        )
    else:
        age = _format_age(now - channel.health.checked_at)
        if channel.health.error is not None:
            error = escape(_truncate(channel.health.error, 240))
            details = (
                f"проверен: {age}; ошибка: {error}; "
                f"позиция поллера: {position}"
            )
        elif kind == "warning":
            details = (
                f"статус: давно не проверялся ({age}); "
                f"позиция поллера: {position}"
            )
        else:
            details = f"проверен: {age}; позиция поллера: {position}"

    return kind, f"{first_line}\n{details}"


def _split_report(header: str, entries: list[str]) -> list[str]:
    if not entries:
        return [header + "\n\nКаналы мониторинга отсутствуют."]

    continuation = "📡 <b>Статус каналов мониторинга — продолжение</b>"
    messages = []
    current = header

    for entry in entries:
        candidate = current + "\n\n" + entry
        if len(candidate) > REPORT_CHUNK_LIMIT:
            messages.append(current)
            current = continuation + "\n\n" + entry
        else:
            current = candidate

    messages.append(current)
    return messages


def build_channels_status_messages(
    channels: list[ChannelStatusData],
    *,
    now: float,
    stale_after_sec: int,
    poller_enabled: bool,
    userbot_connected: bool,
) -> list[str]:
    """Формирует полную HTML-сводку, разбитую под лимит Telegram."""
    formatted_entries = []
    counts = {"ok": 0, "warning": 0, "error": 0}

    for index, channel in enumerate(channels, start=1):
        kind, entry = _format_channel(
            index,
            channel,
            now=now,
            stale_after_sec=stale_after_sec,
        )
        counts[kind] += 1
        formatted_entries.append(entry)

    poller_status = "✅ включён" if poller_enabled else "⛔ выключен"
    userbot_status = "✅ подключён" if userbot_connected else "❌ отключён"
    header = (
        "📡 <b>Статус каналов мониторинга</b>\n"
        f"Поллер: {poller_status}\n"
        f"Userbot: {userbot_status}\n"
        f"Всего: {len(channels)} | ✅ {counts['ok']} | "
        f"⚠️ {counts['warning']} | ❌ {counts['error']}"
    )
    return _split_report(header, formatted_entries)
