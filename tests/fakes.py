"""Фейки для тестов поллера: без реальных Telegram и Redis."""


class FakeMessage:
    def __init__(self, message_id: int, chat_id: int, media_group_id=None):
        self.id = message_id
        self.chat = type("Chat", (), {"id": chat_id})()
        self.media_group_id = media_group_id


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
    def __init__(self, last_ids=None, seen=None):
        self.last_ids = dict(last_ids or {})
        self.seen = set(seen or [])

    async def get_last_id(self, chat_id):
        return self.last_ids.get(chat_id)

    async def set_last_id(self, chat_id, message_id):
        self.last_ids[chat_id] = message_id

    async def is_seen(self, chat_id, message_id):
        return (chat_id, message_id) in self.seen

    async def mark_seen(self, chat_id, message_id):
        self.seen.add((chat_id, message_id))


class RecordingHandler:
    def __init__(self, error=None):
        self.calls = []
        self.error = error

    async def __call__(self, client, message):
        self.calls.append(message.id)
        if self.error is not None:
            raise self.error
