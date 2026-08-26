from dataclasses import dataclass


DEFAULT_MESSAGE_COUNT = 100
MAX_MESSAGE_COUNT = 500


class CheckRequestError(ValueError):
    pass


@dataclass(frozen=True)
class CheckRequest:
    channel: str
    message_count: int


def parse_check_request(text: str | None) -> CheckRequest:
    parts = (text or "").strip().split()
    if len(parts) not in (2, 3):
        raise CheckRequestError(
            "⚠️ Укажи канал и количество сообщений в формате:\n"
            "<code>/check @channel [1-500]</code>"
        )

    channel = parts[1]
    if not channel.startswith("@") or channel == "@":
        raise CheckRequestError(
            "⚠️ Канал должен быть в формате <code>@channel</code>"
        )

    message_count = DEFAULT_MESSAGE_COUNT
    if len(parts) == 3:
        try:
            message_count = int(parts[2])
        except ValueError as ex:
            raise CheckRequestError(
                "⚠️ Количество сообщений должно быть целым числом от 1 до 500"
            ) from ex

    if not 1 <= message_count <= MAX_MESSAGE_COUNT:
        raise CheckRequestError(
            "⚠️ Количество сообщений должно быть целым числом от 1 до 500"
        )

    return CheckRequest(channel=channel, message_count=message_count)


async def collect_requested_posts(parser, request: CheckRequest):
    return await parser.get_last_posts(
        channel=request.channel,
        limit=request.message_count,
        load_media_binary=True,
    )
