from app.userbot.poller import ChannelPoller
from tests.fakes import FakeClient, FakeMessage, FakeState, RecordingHandler

CHAT_ID = -1001297561296


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


async def test_seen_message_is_skipped_but_position_advances():
    messages = [FakeMessage(102, CHAT_ID), FakeMessage(101, CHAT_ID)]
    state = FakeState(last_ids={CHAT_ID: 100}, seen={(CHAT_ID, 101)})
    handler = RecordingHandler()
    poller = make_poller({CHAT_ID: messages}, state, handler)

    processed = await poller.poll_channel(CHAT_ID, limit=50)

    assert processed == 1
    assert handler.calls == [102]
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


async def test_limit_is_passed_to_client():
    messages = [FakeMessage(101, CHAT_ID)]
    state = FakeState(last_ids={CHAT_ID: 100})
    handler = RecordingHandler()
    client = FakeClient(history={CHAT_ID: messages})
    poller = ChannelPoller(client=client, handler=handler, state=state, sleep=_noop_sleep)

    await poller.poll_channel(CHAT_ID, limit=25)

    assert client.calls == [(CHAT_ID, 25)]
