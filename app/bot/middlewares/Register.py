import typing
from aiogram import types, BaseMiddleware
from app.database.repo.User import UserRepo


class RegisterMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: typing.Callable[[types.TelegramObject, typing.Dict[str, typing.Any]], typing.Awaitable[typing.Any]],
        event: types.TelegramObject,
        data: typing.Dict[str, typing.Any],
    ) -> typing.Any:
        user, is_first = await UserRepo.update_or_create(
            telegram_id=event.from_user.id,
            full_name=event.from_user.full_name,
            username=event.from_user.username,
        )

        data["user"] = user
        data["is_first"] = is_first

        return await handler(event, data)
