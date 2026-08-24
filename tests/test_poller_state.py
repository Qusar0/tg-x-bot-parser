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

    async def set_if_absent(self, key: str, value: str, expire_sec: int) -> bool:
        if key in self.data:
            return False
        self.data[key] = value
        self.ttls[key] = expire_sec
        return True

    async def delete_key(self, key: str) -> None:
        self.data.pop(key, None)
        self.ttls.pop(key, None)


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


async def test_channel_health_round_trip_for_success(store):
    await poller_state.set_channel_health(-100500, checked_at=1234.5)

    health = await poller_state.get_channel_health(-100500)

    assert health == poller_state.ChannelHealth(checked_at=1234.5, error=None)


async def test_channel_health_round_trip_for_error(store):
    await poller_state.set_channel_health(
        -100500,
        checked_at=1234.5,
        error="CHANNEL_PRIVATE",
    )

    health = await poller_state.get_channel_health(-100500)

    assert health == poller_state.ChannelHealth(
        checked_at=1234.5,
        error="CHANNEL_PRIVATE",
    )


async def test_get_channel_health_returns_none_when_missing(store):
    assert await poller_state.get_channel_health(-100500) is None


async def test_get_channel_health_returns_none_for_malformed_value(store):
    store.data["poller:health:-100500"] = "not-json"

    assert await poller_state.get_channel_health(-100500) is None


@pytest.mark.parametrize("value", ["[]", "null", '"text"'])
async def test_get_channel_health_returns_none_for_wrong_json_shape(store, value):
    store.data["poller:health:-100500"] = value

    assert await poller_state.get_channel_health(-100500) is None


@pytest.mark.parametrize("checked_at", ["NaN", "Infinity", "-Infinity"])
async def test_get_channel_health_returns_none_for_non_finite_time(
    store,
    checked_at,
):
    store.data["poller:health:-100500"] = (
        f'{{"checked_at": {checked_at}, "error": null}}'
    )

    assert await poller_state.get_channel_health(-100500) is None


async def test_poller_heartbeat_round_trip(store):
    await poller_state.set_poller_heartbeat(
        checked_at=1234.5,
        status="ok",
    )

    heartbeat = await poller_state.get_poller_heartbeat()

    assert heartbeat == poller_state.PollerHeartbeat(
        checked_at=1234.5,
        status="ok",
        error=None,
    )


async def test_poller_heartbeat_round_trip_for_error(store):
    await poller_state.set_poller_heartbeat(
        checked_at=1234.5,
        status="error",
        error="RuntimeError: failure",
    )

    heartbeat = await poller_state.get_poller_heartbeat()

    assert heartbeat == poller_state.PollerHeartbeat(
        checked_at=1234.5,
        status="error",
        error="RuntimeError: failure",
    )


@pytest.mark.parametrize("value", [None, "[]", "not-json"])
async def test_get_poller_heartbeat_returns_none_for_missing_or_malformed_value(
    store,
    value,
):
    if value is not None:
        store.data[poller_state.POLLER_HEARTBEAT_KEY] = value

    assert await poller_state.get_poller_heartbeat() is None


@pytest.mark.parametrize("checked_at", ["NaN", "Infinity", "-Infinity"])
async def test_get_poller_heartbeat_returns_none_for_non_finite_time(
    store,
    checked_at,
):
    store.data[poller_state.POLLER_HEARTBEAT_KEY] = (
        f'{{"checked_at": {checked_at}, "status": "ok", "error": null}}'
    )

    assert await poller_state.get_poller_heartbeat() is None


async def test_claim_message_succeeds_once_with_ttl(store):
    assert await poller_state.claim_message(-100500, 7) is True
    assert store.ttls["poller:seen:-100500:7"] == poller_state.SEEN_TTL_SEC


async def test_claim_message_fails_on_repeat_claim(store):
    assert await poller_state.claim_message(-100500, 7) is True

    assert await poller_state.claim_message(-100500, 7) is False


async def test_release_message_allows_claim_again(store):
    assert await poller_state.claim_message(-100500, 7) is True

    await poller_state.release_message(-100500, 7)

    assert await poller_state.claim_message(-100500, 7) is True


async def test_claim_message_is_independent_per_message_and_chat(store):
    """Регрессия: захват одного сообщения не должен блокировать другое сообщение
    того же чата или то же сообщение другого чата — ключ учитывает оба поля."""
    assert await poller_state.claim_message(-100500, 7) is True

    assert await poller_state.claim_message(-100500, 8) is True
    assert await poller_state.claim_message(-100600, 7) is True


async def test_claim_group_send_succeeds_once_with_ttl(store):
    assert await poller_state.claim_group_send(-100500, "13835058055", -200600) is True
    assert store.ttls["poller:group:-100500:13835058055:-200600"] == poller_state.SEEN_TTL_SEC


async def test_claim_group_send_fails_on_repeat_claim(store):
    assert await poller_state.claim_group_send(-100500, "13835058055", -200600) is True

    assert await poller_state.claim_group_send(-100500, "13835058055", -200600) is False


async def test_claim_group_send_is_scoped_per_destination_chat(store):
    """Захват альбома для одного чата-получателя не должен блокировать другой.

    Регрессия: раньше ключ не учитывал чат-получателя, из-за чего при рассылке
    одного альбома в несколько центральных чатов второй и последующие получатели
    молча не получали альбом (claim для них ошибочно бы проваливался).
    """
    source_chat_id = -100500
    group_id = "13835058055"
    dest_chat_a = -200600
    dest_chat_b = -200700

    assert await poller_state.claim_group_send(source_chat_id, group_id, dest_chat_a) is True

    assert await poller_state.claim_group_send(source_chat_id, group_id, dest_chat_b) is True


async def test_release_group_send_allows_claim_again(store):
    assert await poller_state.claim_group_send(-100500, "13835058055", -200600) is True

    await poller_state.release_group_send(-100500, "13835058055", -200600)

    assert await poller_state.claim_group_send(-100500, "13835058055", -200600) is True
