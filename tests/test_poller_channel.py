from datetime import datetime, timedelta

from app.userbot.poller import ChannelPoller
from tests.fakes import FakeClient, FakeMessage, FakeState, RecordingHandler

CHAT_ID = -1001297561296
MAX_AGE_SEC = 3600


def make_poller(history, state, handler):
    return ChannelPoller(
        client=FakeClient(history=history),
        handler=handler,
        state=state,
        sleep=_noop_sleep,
    )


async def _noop_sleep(_seconds):
    return None


async def test_bootstrap_records_position_without_processing():
    messages = [FakeMessage(105, CHAT_ID), FakeMessage(104, CHAT_ID)]
    state = FakeState()
    handler = RecordingHandler()
    poller = make_poller({CHAT_ID: messages}, state, handler)

    processed = await poller.poll_channel(CHAT_ID, limit=50)

    assert processed == 0
    assert handler.calls == []
    assert state.last_ids[CHAT_ID] == 105


async def test_new_messages_processed_in_chronological_order():
    messages = [FakeMessage(103, CHAT_ID), FakeMessage(102, CHAT_ID), FakeMessage(101, CHAT_ID)]
    state = FakeState(last_ids={CHAT_ID: 100})
    handler = RecordingHandler()
    poller = make_poller({CHAT_ID: messages}, state, handler)

    processed = await poller.poll_channel(CHAT_ID, limit=50)

    assert processed == 3
    assert handler.calls == [101, 102, 103]
    assert state.last_ids[CHAT_ID] == 103


async def test_old_messages_are_not_processed():
    messages = [FakeMessage(100, CHAT_ID), FakeMessage(99, CHAT_ID)]
    state = FakeState(last_ids={CHAT_ID: 100})
    handler = RecordingHandler()
    poller = make_poller({CHAT_ID: messages}, state, handler)

    processed = await poller.poll_channel(CHAT_ID, limit=50)

    assert processed == 0
    assert handler.calls == []


async def test_all_new_messages_reach_handler_without_poller_side_dedup():
    """Поллер больше не решает сам, обрабатывать ли сообщение, сверяясь с
    отметкой о том, что оно уже обработано (раньше — своя проверка перед
    вызовом handler). Это решение теперь исключительно за обработчиком
    (атомарный claim_message): если бы поллер продолжил сам отбраковывать
    сообщения неатомарно относительно захвата в обработчике, могла бы
    вернуться дыра — сообщение потерялось бы, если кто-то другой уже
    застолбил ключ, но ничего не отправил. Поэтому каждое новое сообщение
    обязано дойти до handler ровно один раз за обход, а position должен
    продвинуться до самого свежего id независимо от этого.
    """
    messages = [FakeMessage(102, CHAT_ID), FakeMessage(101, CHAT_ID)]
    state = FakeState(last_ids={CHAT_ID: 100})
    handler = RecordingHandler()
    poller = make_poller({CHAT_ID: messages}, state, handler)

    processed = await poller.poll_channel(CHAT_ID, limit=50)

    assert processed == 2
    assert handler.calls == [101, 102]
    assert state.last_ids[CHAT_ID] == 102


async def test_handler_error_does_not_stop_remaining_messages():
    messages = [FakeMessage(102, CHAT_ID), FakeMessage(101, CHAT_ID)]
    state = FakeState(last_ids={CHAT_ID: 100})
    handler = RecordingHandler(error=RuntimeError("боевой сбой"))
    poller = make_poller({CHAT_ID: messages}, state, handler)

    processed = await poller.poll_channel(CHAT_ID, limit=50)

    assert processed == 0
    assert handler.calls == [101, 102]
    assert state.last_ids[CHAT_ID] == 102


async def test_stale_message_is_not_processed_but_advances_position():
    """Находка 1: после простоя одинокое старое сообщение не должно уйти в чаты
    заказчика, но позиция обязана продвинуться, иначе канал застрянет навсегда."""
    old_date = datetime.now() - timedelta(hours=2)
    messages = [FakeMessage(101, CHAT_ID, date=old_date)]
    state = FakeState(last_ids={CHAT_ID: 100})
    handler = RecordingHandler()
    poller = make_poller({CHAT_ID: messages}, state, handler)

    processed = await poller.poll_channel(CHAT_ID, limit=50, max_age_sec=MAX_AGE_SEC)

    assert processed == 0
    assert handler.calls == []
    assert state.last_ids[CHAT_ID] == 101


async def test_fresh_message_is_processed_with_age_filter_enabled():
    messages = [FakeMessage(101, CHAT_ID)]  # дата по умолчанию — "сейчас"
    state = FakeState(last_ids={CHAT_ID: 100})
    handler = RecordingHandler()
    poller = make_poller({CHAT_ID: messages}, state, handler)

    processed = await poller.poll_channel(CHAT_ID, limit=50, max_age_sec=MAX_AGE_SEC)

    assert processed == 1
    assert handler.calls == [101]
    assert state.last_ids[CHAT_ID] == 101


async def test_stale_backlog_advances_position_to_newest_without_processing():
    """Находка 1: после долгого простоя весь накопленный бэклог старый — ничего
    не отправляем в боевые чаты, но позиция уезжает к самому свежему id, чтобы
    канал не застрял на старом хвосте навсегда."""
    old_date = datetime.now() - timedelta(hours=5)
    messages = [
        FakeMessage(105, CHAT_ID, date=old_date),
        FakeMessage(104, CHAT_ID, date=old_date),
        FakeMessage(103, CHAT_ID, date=old_date),
    ]
    state = FakeState(last_ids={CHAT_ID: 100})
    handler = RecordingHandler()
    poller = make_poller({CHAT_ID: messages}, state, handler)

    processed = await poller.poll_channel(CHAT_ID, limit=50, max_age_sec=MAX_AGE_SEC)

    assert processed == 0
    assert handler.calls == []
    assert state.last_ids[CHAT_ID] == 105


async def test_mixed_stale_and_fresh_only_fresh_reaches_handler():
    """Смешанный бэклог: старые посты из простоя пропускаем, свежий — доставляем,
    позиция продвигается через все прочитанные сообщения."""
    old_date = datetime.now() - timedelta(hours=3)
    messages = [
        FakeMessage(105, CHAT_ID),  # свежее
        FakeMessage(104, CHAT_ID, date=old_date),
        FakeMessage(103, CHAT_ID, date=old_date),
    ]
    state = FakeState(last_ids={CHAT_ID: 100})
    handler = RecordingHandler()
    poller = make_poller({CHAT_ID: messages}, state, handler)

    processed = await poller.poll_channel(CHAT_ID, limit=50, max_age_sec=MAX_AGE_SEC)

    assert processed == 1
    assert handler.calls == [105]
    assert state.last_ids[CHAT_ID] == 105


async def test_age_filter_disabled_by_default_keeps_old_behavior():
    """Без явного max_age_sec (как в существующих тестах) фильтр по возрасту не
    должен применяться — обратная совместимость для вызовов без этого параметра."""
    old_date = datetime.now() - timedelta(hours=10)
    messages = [FakeMessage(101, CHAT_ID, date=old_date)]
    state = FakeState(last_ids={CHAT_ID: 100})
    handler = RecordingHandler()
    poller = make_poller({CHAT_ID: messages}, state, handler)

    processed = await poller.poll_channel(CHAT_ID, limit=50)

    assert processed == 1
    assert handler.calls == [101]


async def test_limit_is_passed_to_client():
    messages = [FakeMessage(101, CHAT_ID)]
    state = FakeState(last_ids={CHAT_ID: 100})
    handler = RecordingHandler()
    client = FakeClient(history={CHAT_ID: messages})
    poller = ChannelPoller(client=client, handler=handler, state=state, sleep=_noop_sleep)

    await poller.poll_channel(CHAT_ID, limit=25)

    assert client.calls == [(CHAT_ID, 25)]
