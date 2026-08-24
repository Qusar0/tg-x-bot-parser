"""Состояние поллера в Redis: позиции чтения и отметки обработанных сообщений.

Ключи вынесены под префикс poller:, чтобы чистка старых постов
(cleanup_old_posts удаляет post:*) их не задевала.
"""
import json
from dataclasses import dataclass

from loguru import logger

LAST_ID_KEY = "poller:last_id:{chat_id}"
HEALTH_KEY = "poller:health:{chat_id}"
POLLER_HEARTBEAT_KEY = "poller:heartbeat"
SEEN_KEY = "poller:seen:{chat_id}:{message_id}"
GROUP_KEY = "poller:group:{chat_id}:{media_group_id}:{dest_chat_id}"

SEEN_TTL_SEC = 48 * 60 * 60
POLLER_HEARTBEAT_STATUSES = {
    "running",
    "ok",
    "disabled",
    "waiting_userbot",
    "error",
}

# Подменяется в тестах; в бою резолвится лениво, чтобы не тянуть app.config при импорте
_store = None


@dataclass(frozen=True)
class ChannelHealth:
    checked_at: float
    error: str | None = None


@dataclass(frozen=True)
class PollerHeartbeat:
    checked_at: float
    status: str
    error: str | None = None


def _get_store():
    if _store is not None:
        return _store

    from app.database.redis import redis_store

    return redis_store


async def get_last_id(chat_id: int) -> int | None:
    value = await _get_store().get_value(LAST_ID_KEY.format(chat_id=chat_id))
    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        logger.warning(f"Поллер: некорректная позиция для чата {chat_id}: {value!r}")
        return None


async def set_last_id(chat_id: int, message_id: int) -> None:
    await _get_store().set_value(LAST_ID_KEY.format(chat_id=chat_id), str(message_id))


async def set_channel_health(
    chat_id: int,
    *,
    checked_at: float,
    error: str | None = None,
) -> None:
    payload = json.dumps(
        {"checked_at": float(checked_at), "error": error},
        ensure_ascii=False,
    )
    await _get_store().set_value(HEALTH_KEY.format(chat_id=chat_id), payload)


async def get_channel_health(chat_id: int) -> ChannelHealth | None:
    value = await _get_store().get_value(HEALTH_KEY.format(chat_id=chat_id))
    if value is None:
        return None

    try:
        payload = json.loads(value)
        if not isinstance(payload, dict):
            raise TypeError("health payload must be an object")
        error = payload.get("error")
        if error is not None and not isinstance(error, str):
            raise ValueError("error must be a string or null")
        return ChannelHealth(
            checked_at=float(payload["checked_at"]),
            error=error,
        )
    except (TypeError, ValueError, KeyError, json.JSONDecodeError):
        logger.warning(f"Поллер: некорректное состояние здоровья чата {chat_id}: {value!r}")
        return None


async def set_poller_heartbeat(
    *,
    checked_at: float,
    status: str,
    error: str | None = None,
) -> None:
    if status not in POLLER_HEARTBEAT_STATUSES:
        raise ValueError(f"unknown poller heartbeat status: {status}")
    payload = json.dumps(
        {
            "checked_at": float(checked_at),
            "status": status,
            "error": error,
        },
        ensure_ascii=False,
    )
    await _get_store().set_value(POLLER_HEARTBEAT_KEY, payload)


async def get_poller_heartbeat() -> PollerHeartbeat | None:
    value = await _get_store().get_value(POLLER_HEARTBEAT_KEY)
    if value is None:
        return None

    try:
        payload = json.loads(value)
        if not isinstance(payload, dict):
            raise TypeError("poller heartbeat payload must be an object")
        status = payload["status"]
        if status not in POLLER_HEARTBEAT_STATUSES:
            raise ValueError("unknown poller heartbeat status")
        error = payload.get("error")
        if error is not None and not isinstance(error, str):
            raise ValueError("error must be a string or null")
        return PollerHeartbeat(
            checked_at=float(payload["checked_at"]),
            status=status,
            error=error,
        )
    except (TypeError, ValueError, KeyError, json.JSONDecodeError):
        logger.warning(f"Поллер: некорректный heartbeat: {value!r}")
        return None


async def claim_message(chat_id: int, message_id: int) -> bool:
    """Атомарно захватывает право обработать сообщение (SET NX EX).

    Между проверкой "не обработано ли уже" и последующей отметкой раньше был
    await, на котором живой push-апдейт и обход поллера могли одновременно
    проскочить проверку и оба отправить сообщение дальше. Захват через
    set_if_absent убирает это окно: побеждает тот, кто застолбил ключ первым.

    Возвращает True, если сообщение видим впервые и его нужно обрабатывать,
    False — если ключ уже занят (кто-то другой уже обрабатывает или обработал
    это сообщение).
    """
    key = SEEN_KEY.format(chat_id=chat_id, message_id=message_id)
    return await _get_store().set_if_absent(key, "1", SEEN_TTL_SEC)


async def release_message(chat_id: int, message_id: int) -> None:
    """Освобождает захват, чтобы повторная обработка сообщения осталась возможной."""
    key = SEEN_KEY.format(chat_id=chat_id, message_id=message_id)
    await _get_store().delete_key(key)


async def claim_group_send(chat_id: int, media_group_id: str, dest_chat_id: int) -> bool:
    """Атомарно захватывает право отправить альбом в dest_chat_id.

    Возвращает True, если захват удался (можно отправлять), False — если
    альбом уже захвачен (кто-то другой уже отправляет или отправил).
    """
    key = GROUP_KEY.format(chat_id=chat_id, media_group_id=media_group_id, dest_chat_id=dest_chat_id)
    return await _get_store().set_if_absent(key, "1", SEEN_TTL_SEC)


async def release_group_send(chat_id: int, media_group_id: str, dest_chat_id: int) -> None:
    """Освобождает захват, чтобы повторная отправка альбома осталась возможной."""
    key = GROUP_KEY.format(chat_id=chat_id, media_group_id=media_group_id, dest_chat_id=dest_chat_id)
    await _get_store().delete_key(key)
