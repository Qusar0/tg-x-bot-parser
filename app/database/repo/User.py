from app.database.models.User import User


class UserRepo:
    @staticmethod
    async def update_or_create(telegram_id: int, full_name: str, username: str = None) -> User:
        user = await User.filter(telegram_id=telegram_id).first()
        is_first = False

        if not user:
            user = await User.create(telegram_id=telegram_id, full_name=full_name, username=username)
            is_first = True
        else:
            user.telegram_id = telegram_id
            user.full_name = full_name
            user.username = username
            await user.save(update_fields=["telegram_id", "full_name", "username"])

        return user, is_first

    @staticmethod
    async def delete_banned_users(user_entities: list[str]) -> bool:
        for user_entity in user_entities:
            if user_entity.isnumeric():
                await User.filter(telegram_id=int(user_entity)).delete()
            else:
                await User.filter(username=user_entity.replace("@", "")).delete()

        return True

    @staticmethod
    async def delete_user_by_telegram_id(telegram_id: int):
        await User.filter(telegram_id=telegram_id).delete()
        return True

    @staticmethod
    async def get_all() -> list[User]:
        users = await User.all()
        return users

    @staticmethod
    async def get_by_telegram_id(telegram_id: int) -> User:
        user = await User.filter(telegram_id=telegram_id).first()
        return user

    @staticmethod
    async def get_by_username(username: str) -> User | None:
        user = await User.filter(username=username).first()
        return user
