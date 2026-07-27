from pyrogram.errors import FloodWait

from app.userbot.poller import ChannelPoller
from tests.fakes import FakeClient, FakeMessage, FakeState, RecordingHandler

CHAT_A = -1001297561296
CHAT_B = -1001727857237


class FakeChat:
    def __init__(self, telegram_id):
        self.telegram_id = telegram_id


class FakeSettings:
    """Настройки поллера без обращения к app.settings."""

    def __init__(self, enabled=True, interval=300, limit=50, delay=2):
        self._enabled = enabled
        self._interval = interval
        self._limit = limit
        self._delay = delay

    def get_poller_enabled(self):
        return self._enabled

    def get_poller_interval_sec(self):
        return self._interval

    def get_poller_limit(self):
        return self._limit

    def get_poller_channel_delay_sec(self):
        return self._delay


class SleepRecorder:
    def __init__(self):
        self.calls = []

    async def __call__(self, seconds):
        self.calls.append(seconds)


def make_chats_provider(chat_ids):
    async def provider():
        return [FakeChat(chat_id) for chat_id in chat_ids]

    return provider


async def test_poll_once_walks_all_channels():
    history = {
        CHAT_A: [FakeMessage(101, CHAT_A)],
        CHAT_B: [FakeMessage(201, CHAT_B)],
    }
    state = FakeState(last_ids={CHAT_A: 100, CHAT_B: 200})
    handler = RecordingHandler()
    poller = ChannelPoller(
        client=FakeClient(history=history),
        handler=handler,
        chats_provider=make_chats_provider([CHAT_A, CHAT_B]),
        state=state,
        sleep=SleepRecorder(),
        settings=FakeSettings(),
    )

    total = await poller.poll_once()

    assert total == 2
    assert sorted(handler.calls) == [101, 201]


async def test_poll_once_pauses_between_channels():
    state = FakeState(last_ids={CHAT_A: 100, CHAT_B: 200})
    sleeper = SleepRecorder()
    poller = ChannelPoller(
        client=FakeClient(history={}),
        handler=RecordingHandler(),
        chats_provider=make_chats_provider([CHAT_A, CHAT_B]),
        state=state,
        sleep=sleeper,
        settings=FakeSettings(),
    )

    await poller.poll_once()

    assert len(sleeper.calls) == 2


async def test_channel_error_does_not_stop_the_walk():
    state = FakeState(last_ids={CHAT_A: 100, CHAT_B: 200})
    handler = RecordingHandler()

    class BrokenForFirstChat(FakeClient):
        def get_chat_history(self, chat_id, limit=100):
            if chat_id == CHAT_A:
                raise ValueError("канал недоступен")
            return super().get_chat_history(chat_id, limit=limit)

    client = BrokenForFirstChat(history={CHAT_B: [FakeMessage(201, CHAT_B)]})
    poller = ChannelPoller(
        client=client,
        handler=handler,
        chats_provider=make_chats_provider([CHAT_A, CHAT_B]),
        state=state,
        sleep=SleepRecorder(),
        settings=FakeSettings(),
    )

    total = await poller.poll_once()

    assert total == 1
    assert handler.calls == [201]


async def test_floodwait_is_awaited_and_walk_continues():
    state = FakeState(last_ids={CHAT_A: 100, CHAT_B: 200})
    handler = RecordingHandler()
    sleeper = SleepRecorder()

    class FloodOnFirstChat(FakeClient):
        def get_chat_history(self, chat_id, limit=100):
            if chat_id == CHAT_A:
                raise FloodWait(value=17)
            return super().get_chat_history(chat_id, limit=limit)

    client = FloodOnFirstChat(history={CHAT_B: [FakeMessage(201, CHAT_B)]})
    poller = ChannelPoller(
        client=client,
        handler=handler,
        chats_provider=make_chats_provider([CHAT_A, CHAT_B]),
        state=state,
        sleep=sleeper,
        settings=FakeSettings(),
    )

    total = await poller.poll_once()

    assert total == 1
    assert 17 in sleeper.calls
