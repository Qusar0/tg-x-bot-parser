"""Состояние поллера в Redis: позиции чтения и отметки обработанных сообщений.

Ключи вынесены под префикс poller:, чтобы чистка старых постов
(cleanup_old_posts удаляет post:*) их не задевала.
"""
from loguru import logger

LAST_ID_KEY = "poller:last_id:{chat_id}"
SEEN_KEY = "poller:seen:{chat_id}:{message_id}"
GROUP_KEY = "poller:group:{chat_id}:{media_group_id}:{dest_chat_id}"

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
