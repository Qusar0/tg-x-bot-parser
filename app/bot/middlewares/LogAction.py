import typing
from aiogram import BaseMiddleware, types
from loguru import logger


def get_user_info(user: types.User) -> str:
    return f"{user.id} | {user.full_name} | @{user.username if user.username else 'Отсутствует'}"


class LogActionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: typing.Callable[[types.TelegramObject, typing.Dict[str, typing.Any]], typing.Awaitable[typing.Any]],
        event: types.TelegramObject,
        data: typing.Dict[str, typing.Any],
    ) -> typing.Any:
        if isinstance(event, types.Message):
            logger.info(f"{get_user_info(event.from_user)} - сообщение: {event.text}")
        elif isinstance(event, types.CallbackQuery):
            logger.info(f"{get_user_info(event.from_user)} - action: {event.data}")

        return await handler(event, data)
