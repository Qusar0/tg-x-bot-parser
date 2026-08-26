import pytest

from app.userbot.check_request import (
    CheckRequest,
    CheckRequestError,
    collect_requested_posts,
    parse_check_request,
)


def test_check_request_uses_100_messages_by_default():
    assert parse_check_request("/check @channel") == CheckRequest(
        channel="@channel",
        message_count=100,
    )


@pytest.mark.parametrize("message_count", [1, 100, 500])
def test_check_request_accepts_explicit_message_count(message_count):
    assert parse_check_request(f"/check @channel {message_count}") == CheckRequest(
        channel="@channel",
        message_count=message_count,
    )


@pytest.mark.parametrize(
    "value",
    ["0", "-1", "501", "100.5", "1_0", "many"],
)
def test_check_request_rejects_invalid_message_count(value):
    with pytest.raises(CheckRequestError):
        parse_check_request(f"/check @channel {value}")


@pytest.mark.parametrize(
    "text",
    [
        None,
        "",
        "/check",
        "/check channel",
        "/check @channel 100 extra",
    ],
)
def test_check_request_rejects_invalid_syntax(text):
    with pytest.raises(CheckRequestError):
        parse_check_request(text)


@pytest.mark.parametrize(
    ("command", "expected_count"),
    [
        ("/check @channel", 100),
        ("/check @channel 1", 1),
        ("/check @channel 137", 137),
        ("/check @channel 500", 500),
    ],
)
async def test_collect_requested_posts_passes_message_limit_to_parser(
    command,
    expected_count,
):
    class FakeParser:
        async def get_last_posts(self, *, channel, limit, load_media_binary):
            if channel != "@channel" or not load_media_binary:
                return []
            return list(range(limit))

    request = parse_check_request(command)

    posts = await collect_requested_posts(FakeParser(), request)

    assert len(posts) == expected_count
