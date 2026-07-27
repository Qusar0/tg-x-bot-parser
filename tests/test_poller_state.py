import pytest

from app.userbot import poller_state


class FakeRedisStore:
    """Фейковое хранилище с интерфейсом RedisStore."""

    def __init__(self):
        self.data = {}
        self.ttls = {}

    async def get_value(self, key: str):
        return self.data.get(key)

    async def set_value(self, key: str, value: str):
        self.data[key] = value

    async def set_value_ex(self, key: str, value: str, expire_sec: int):
        self.data[key] = value
        self.ttls[key] = expire_sec


@pytest.fixture
def store(monkeypatch):
    fake = FakeRedisStore()
    monkeypatch.setattr(poller_state, "_store", fake)
    return fake


async def test_get_last_id_returns_none_when_missing(store):
    assert await poller_state.get_last_id(-100500) is None


async def test_set_and_get_last_id(store):
    await poller_state.set_last_id(-100500, 42)

    assert await poller_state.get_last_id(-100500) == 42
    assert store.data["poller:last_id:-100500"] == "42"


async def test_get_last_id_returns_none_on_broken_value(store):
    store.data["poller:last_id:-100500"] = "не число"

    assert await poller_state.get_last_id(-100500) is None


async def test_seen_marks_message_with_ttl(store):
    assert await poller_state.is_seen(-100500, 7) is False

    await poller_state.mark_seen(-100500, 7)

    assert await poller_state.is_seen(-100500, 7) is True
    assert store.ttls["poller:seen:-100500:7"] == poller_state.SEEN_TTL_SEC


async def test_group_sent_marks_album_with_ttl(store):
    assert await poller_state.is_group_sent(-100500, "13835058055", -200600) is False

    await poller_state.mark_group_sent(-100500, "13835058055", -200600)

    assert await poller_state.is_group_sent(-100500, "13835058055", -200600) is True
    assert store.ttls["poller:group:-100500:13835058055:-200600"] == poller_state.SEEN_TTL_SEC


async def test_group_sent_is_scoped_per_destination_chat(store):
    """Отметка альбома для одного чата-получателя не должна влиять на другой.

    Регрессия: раньше ключ не учитывал чат-получателя, из-за чего при рассылке
    одного альбома в несколько центральных чатов второй и последующие получатели
    молча не получали альбом (is_group_sent ошибочно возвращал True).
    """
    source_chat_id = -100500
    group_id = "13835058055"
    dest_chat_a = -200600
    dest_chat_b = -200700

    await poller_state.mark_group_sent(source_chat_id, group_id, dest_chat_a)

    assert await poller_state.is_group_sent(source_chat_id, group_id, dest_chat_a) is True
    assert await poller_state.is_group_sent(source_chat_id, group_id, dest_chat_b) is False
