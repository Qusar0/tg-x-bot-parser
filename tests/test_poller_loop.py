import pytest
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

    def __init__(self, enabled=True, interval=300, limit=50, delay=2, max_age_sec=3600):
        self._enabled = enabled
        self._interval = interval
        self._limit = limit
        self._delay = delay
        self._max_age_sec = max_age_sec

    def get_poller_enabled(self):
        return self._enabled

    def get_poller_interval_sec(self):
        return self._interval

    def get_poller_limit(self):
        return self._limit

    def get_poller_channel_delay_sec(self):
        return self._delay

    def get_poller_max_age_sec(self):
        return self._max_age_sec


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


class StopLoop(Exception):
    """Сигнальное исключение: пробивает бесконечный while True в start(),
    чтобы тест мог проверить накопленное состояние без реального ожидания."""


class CountingSleep:
    """Как SleepRecorder, но останавливает цикл после N вызовов через StopLoop."""

    def __init__(self, stop_after: int):
        self.stop_after = stop_after
        self.calls = []

    async def __call__(self, seconds):
        self.calls.append(seconds)
        if len(self.calls) >= self.stop_after:
            raise StopLoop()


class FakeConnClient:
    def __init__(self, is_connected):
        self.is_connected = is_connected


async def test_start_skips_poll_once_when_disabled_by_setting():
    """Находка 4, ветка 1: поллер выключен настройкой poller_enabled — poll_once
    не вызывается, цикл просто ждёт следующей итерации без ошибок."""
    settings = FakeSettings(enabled=False, interval=120)
    sleeper = CountingSleep(stop_after=3)
    poll_calls = []

    poller = ChannelPoller(client=FakeConnClient(True), settings=settings, sleep=sleeper)
    poller.poll_once = _make_recording_poll_once(poll_calls)

    with pytest.raises(StopLoop):
        await poller.start()

    assert poll_calls == []
    assert sleeper.calls == [120, 120, 120]


async def test_start_waits_when_userbot_client_not_connected():
    """Находка 4, ветка 2: клиент ещё не подключён — poll_once не вызывается,
    цикл не падает, а ждёт следующей итерации."""
    settings = FakeSettings(enabled=True, interval=90)
    sleeper = CountingSleep(stop_after=2)
    poll_calls = []

    poller = ChannelPoller(client=FakeConnClient(False), settings=settings, sleep=sleeper)
    poller.poll_once = _make_recording_poll_once(poll_calls)

    with pytest.raises(StopLoop):
        await poller.start()

    assert poll_calls == []
    assert sleeper.calls == [90, 90]


async def test_start_survives_exception_inside_poll_once():
    """Находка 4, ветка 3: исключение внутри poll_once не должно убивать цикл
    (а значит и не должно ронять весь процесс бота через asyncio.gather)."""
    settings = FakeSettings(enabled=True, interval=60)
    sleeper = CountingSleep(stop_after=3)
    poll_calls = []

    async def failing_poll_once():
        poll_calls.append(1)
        raise RuntimeError("боевой сбой обхода")

    poller = ChannelPoller(client=FakeConnClient(True), settings=settings, sleep=sleeper)
    poller.poll_once = failing_poll_once

    with pytest.raises(StopLoop):
        await poller.start()

    assert len(poll_calls) == 3
    assert sleeper.calls == [60, 60, 60]


async def test_start_survives_broken_settings_and_uses_default_interval():
    """Корень находки 4: get_poller_interval_sec() делает int(...) и падает на
    значении вроде '5m' или null. Ошибка должна остаться внутри итерации, а
    пауза — взять безопасный интервал по умолчанию, а не убить цикл/процесс."""

    class BrokenIntervalSettings:
        def get_poller_interval_sec(self):
            raise ValueError("invalid literal for int(): '5m'")

        def get_poller_enabled(self):
            return True

    sleeper = CountingSleep(stop_after=2)
    poll_calls = []

    poller = ChannelPoller(
        client=FakeConnClient(True), settings=BrokenIntervalSettings(), sleep=sleeper
    )
    poller.poll_once = _make_recording_poll_once(poll_calls)

    with pytest.raises(StopLoop):
        await poller.start()

    assert poll_calls == []
    assert sleeper.calls == [ChannelPoller.DEFAULT_INTERVAL_SEC, ChannelPoller.DEFAULT_INTERVAL_SEC]


async def test_start_clamps_non_positive_interval_to_minimum():
    """Защита от горячего цикла: нулевой/отрицательный интервал из настроек не
    должен превратиться в asyncio.sleep(0)."""
    settings = FakeSettings(enabled=True, interval=0)
    sleeper = CountingSleep(stop_after=2)

    poller = ChannelPoller(client=FakeConnClient(True), settings=settings, sleep=sleeper)
    poller.poll_once = _make_recording_poll_once([])

    with pytest.raises(StopLoop):
        await poller.start()

    assert sleeper.calls == [ChannelPoller.MIN_INTERVAL_SEC, ChannelPoller.MIN_INTERVAL_SEC]


def _make_recording_poll_once(poll_calls):
    async def poll_once():
        poll_calls.append(1)
        return 0

    return poll_once
