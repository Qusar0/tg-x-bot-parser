from app.userbot.channel_status import (
    ChannelStatusData,
    build_channels_status_messages,
    get_stale_after_sec,
    get_stale_after_sec_from_settings,
    load_channels_status_data,
)
from app.userbot.poller_state import ChannelHealth, PollerHeartbeat


def test_stale_threshold_allows_three_poller_intervals_with_safe_minimum():
    assert get_stale_after_sec(300) == 900
    assert get_stale_after_sec(0) == 90


def test_stale_threshold_uses_safe_default_for_broken_setting():
    assert get_stale_after_sec("5m") == 900
    assert get_stale_after_sec(None) == 900


def test_stale_threshold_survives_settings_getter_error():
    class BrokenSettings:
        def get_poller_interval_sec(self):
            raise ValueError("invalid interval")

    assert get_stale_after_sec_from_settings(BrokenSettings()) == 900


def test_report_classifies_channels_and_escapes_telegram_html():
    channels = [
        ChannelStatusData(
            telegram_id=-1001,
            title="Alpha & Beta",
            entity="@alpha",
            last_id=101,
            health=ChannelHealth(checked_at=990.0),
        ),
        ChannelStatusData(
            telegram_id=-1002,
            title="Slow",
            entity=None,
            last_id=202,
            health=ChannelHealth(checked_at=800.0),
        ),
        ChannelStatusData(
            telegram_id=-1003,
            title="Private <channel>",
            entity="@private",
            last_id=303,
            health=ChannelHealth(checked_at=995.0, error="CHANNEL_PRIVATE <403>"),
        ),
        ChannelStatusData(
            telegram_id=-1004,
            title="New",
            entity="@new",
            last_id=None,
            health=None,
        ),
    ]

    messages = build_channels_status_messages(
        channels,
        now=1000.0,
        stale_after_sec=60,
        poller_enabled=True,
        poller_heartbeat=PollerHeartbeat(checked_at=995.0, status="ok"),
        userbot_connected=True,
    )

    assert len(messages) == 1
    report = messages[0]
    assert "Поллер: ✅ работает" in report
    assert "Userbot: ✅ подключён" in report
    assert "Всего: 4 | ✅ 1 | ⚠️ 2 | ❌ 1" in report
    assert "✅ <b>Alpha &amp; Beta</b> (@alpha)" in report
    assert "позиция поллера: 101" in report
    assert "⚠️ <b>Slow</b> (-1002)" in report
    assert "давно не проверялся" in report
    assert "❌ <b>Private &lt;channel&gt;</b> (@private)" in report
    assert "CHANNEL_PRIVATE &lt;403&gt;" in report
    assert "⚠️ <b>New</b> (@new)" in report
    assert "ещё не проверен поллером" in report


def test_report_is_split_into_telegram_sized_messages_without_losing_channels():
    channels = [
        ChannelStatusData(
            telegram_id=-(1000 + index),
            title=f"Канал {index} " + "x" * 80,
            entity=f"@channel_{index}",
            last_id=index,
            health=ChannelHealth(checked_at=1000.0),
        )
        for index in range(80)
    ]

    messages = build_channels_status_messages(
        channels,
        now=1001.0,
        stale_after_sec=60,
        poller_enabled=True,
        poller_heartbeat=PollerHeartbeat(checked_at=1000.0, status="ok"),
        userbot_connected=True,
    )

    assert len(messages) > 1
    assert all(len(message) <= 3900 for message in messages)
    assert "Статус каналов мониторинга" in messages[0]
    assert all("продолжение" in message for message in messages[1:])
    joined = "\n".join(messages)
    for index in range(80):
        assert f"Канал {index} " in joined


def test_report_handles_empty_monitoring_list_and_global_failures():
    messages = build_channels_status_messages(
        [],
        now=1000.0,
        stale_after_sec=60,
        poller_enabled=False,
        poller_heartbeat=None,
        userbot_connected=False,
    )

    assert messages == [
        "📡 <b>Статус каналов мониторинга</b>\n"
        "Поллер: ⛔ выключен настройкой\n"
        "Userbot: ❌ отключён\n"
        "Всего: 0 | ✅ 0 | ⚠️ 0 | ❌ 0\n\n"
        "Каналы мониторинга отсутствуют."
    ]


def test_report_warns_when_enabled_poller_has_no_fresh_heartbeat():
    without_heartbeat = build_channels_status_messages(
        [],
        now=1000.0,
        stale_after_sec=60,
        poller_enabled=True,
        poller_heartbeat=None,
        userbot_connected=True,
    )[0]
    stale_heartbeat = build_channels_status_messages(
        [],
        now=1000.0,
        stale_after_sec=60,
        poller_enabled=True,
        poller_heartbeat=PollerHeartbeat(checked_at=900.0, status="ok"),
        userbot_connected=True,
    )[0]

    assert "Поллер: ⚠️ ещё не запускался" in without_heartbeat
    assert "Поллер: ⚠️ давно не подавал признаков работы" in stale_heartbeat


def test_report_shows_poller_error_and_escapes_it():
    report = build_channels_status_messages(
        [],
        now=1000.0,
        stale_after_sec=60,
        poller_enabled=True,
        poller_heartbeat=PollerHeartbeat(
            checked_at=995.0,
            status="error",
            error="Redis <offline>",
        ),
        userbot_connected=True,
    )[0]

    assert "Поллер: ❌ ошибка: Redis &lt;offline&gt;" in report


async def test_load_channels_status_data_matches_redis_state_by_chat_id():
    chats = [
        type(
            "Chat",
            (),
            {
                "telegram_id": -1001,
                "title": "First",
                "entity": "@first",
            },
        )(),
        type(
            "Chat",
            (),
            {
                "telegram_id": -1002,
                "title": "Second",
                "entity": None,
            },
        )(),
    ]

    class State:
        async def get_channel_health(self, chat_id):
            if chat_id == -1001:
                return ChannelHealth(checked_at=900.0)
            return None

        async def get_last_id(self, chat_id):
            return {-1001: 11, -1002: 22}[chat_id]

    result = await load_channels_status_data(chats, State())

    assert result == [
        ChannelStatusData(
            telegram_id=-1001,
            title="First",
            entity="@first",
            last_id=11,
            health=ChannelHealth(checked_at=900.0),
        ),
        ChannelStatusData(
            telegram_id=-1002,
            title="Second",
            entity=None,
            last_id=22,
            health=None,
        ),
    ]
