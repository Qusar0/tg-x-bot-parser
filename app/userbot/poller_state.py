"""Состояние поллера в Redis: позиции чтения и отметки обработанных сообщений.

Ключи вынесены под префикс poller:, чтобы чистка старых постов
(cleanup_old_posts удаляет post:*) их не задевала.
"""
from loguru import logger

LAST_ID_KEY = "poller:last_id:{chat_id}"
SEEN_KEY = "poller:seen:{chat_id}:{message_id}"
GROUP_KEY = "poller:group:{chat_id}:{media_group_id}"

SEEN_TTL_SEC = 48 * 60 * 60

# Подменяется в тестах; в бою резолвится лениво, чтобы не тянуть app.config при импорте
_store = None


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


async def is_seen(chat_id: int, message_id: int) -> bool:
    key = SEEN_KEY.format(chat_id=chat_id, message_id=message_id)
    return await _get_store().get_value(key) is not None


async def mark_seen(chat_id: int, message_id: int) -> None:
    key = SEEN_KEY.format(chat_id=chat_id, message_id=message_id)
    await _get_store().set_value_ex(key, "1", SEEN_TTL_SEC)


async def is_group_sent(chat_id: int, media_group_id: str) -> bool:
    key = GROUP_KEY.format(chat_id=chat_id, media_group_id=media_group_id)
    return await _get_store().get_value(key) is not None


async def mark_group_sent(chat_id: int, media_group_id: str) -> None:
    key = GROUP_KEY.format(chat_id=chat_id, media_group_id=media_group_id)
    await _get_store().set_value_ex(key, "1", SEEN_TTL_SEC)
