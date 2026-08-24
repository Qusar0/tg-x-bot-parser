"""Фейки для тестов поллера: без реальных Telegram и Redis."""

from datetime import datetime


class FakeMessage:
    def __init__(self, message_id: int, chat_id: int, media_group_id=None, date=None):
        self.id = message_id
        self.chat = type("Chat", (), {"id": chat_id})()
        self.media_group_id = media_group_id
        # По умолчанию сообщение считается свежим (текущее время), чтобы
        # существующие тесты, не задающие date, продолжали работать без изменений.
        self.date = date if date is not None else datetime.now()


class FakeClient:
    """История отдаётся свежими-первыми, как у pyrogram."""

    def __init__(self, history=None, error=None):
        self.history = history or {}
        self.error = error
        self.calls = []

    def get_chat_history(self, chat_id, limit=100):
        self.calls.append((chat_id, limit))
        error = self.error
        messages = list(self.history.get(chat_id, []))[:limit]

        async def generator():
            if error is not None:
                raise error
            for message in messages:
                yield message

        return generator()


class FakeState:
    def __init__(self, last_ids=None):
        self.last_ids = dict(last_ids or {})
        self.health = {}
        self.poller_heartbeats = []

    async def get_last_id(self, chat_id):
        return self.last_ids.get(chat_id)

    async def set_last_id(self, chat_id, message_id):
        self.last_ids[chat_id] = message_id

    async def set_channel_health(self, chat_id, *, checked_at, error=None):
        self.health[chat_id] = {
            "checked_at": checked_at,
            "error": error,
        }

    async def set_poller_heartbeat(self, *, checked_at, status, error=None):
        self.poller_heartbeats.append(
            {
                "checked_at": checked_at,
                "status": status,
                "error": error,
            }
        )


class RecordingHandler:
    def __init__(self, error=None):
        self.calls = []
        self.error = error

    async def __call__(self, client, message):
        self.calls.append(message.id)
        if self.error is not None:
            raise self.error
