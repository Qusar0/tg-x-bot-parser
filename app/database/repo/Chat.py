from app.database.models import Chat


class ChatRepo:
    @staticmethod
    async def get_by_telegram_id(telegram_id: int) -> Chat:
        chat = await Chat.filter(telegram_id=telegram_id).first()
        return chat

    @staticmethod
    async def get_by_entity(_entity: str) -> Chat | None:
        chat = await Chat.filter(entity__icontains=_entity.lower()).first()
        return chat

    @staticmethod
    async def get_all() -> list[Chat]:
        chats = await Chat.all()
        return chats

    @staticmethod
    async def add(telegram_id: int, title: str, entity: str | None = None, rating: int = 0) -> Chat:
        chat = await Chat.create(telegram_id=telegram_id, title=title, entity=entity, rating=rating)
        return chat

    @staticmethod
    async def delete(telegram_id: int) -> bool:
        chat = await Chat.filter(telegram_id=telegram_id).first()
        if chat:
            await chat.delete()
            return True

        return False

    @staticmethod
    async def get_by_rating(rating: int) -> list[Chat]:
        chats = await Chat.filter(rating=rating).all()
        return chats

    @staticmethod
    async def get_by_rating_greater_than(min_rating: int) -> list[Chat]:
        chats = await Chat.filter(rating__gt=min_rating).all()
        return chats

    @staticmethod
    async def update_rating(telegram_id: int, rating: int) -> bool:
        chat = await Chat.filter(telegram_id=telegram_id).first()
        if chat:
            chat.rating = rating
            await chat.save()
            return True
        return False

    @staticmethod
    async def get_by_title(title: str) -> Chat | None:
        """Поиск канала по названию (без учета регистра)"""
        chat = await Chat.filter(title__icontains=title).first()
        return chat

    # Central chats
    @staticmethod
    async def get_central_chats() -> list[Chat]:
        chats = await Chat.filter(is_central=True).all()
        return chats

    @staticmethod
    async def add_central_chat(telegram_id: int, title: str, entity: str | None = None) -> Chat:
        chat = await Chat.filter(telegram_id=telegram_id).first()
        if chat:
            chat.title = title or chat.title
            chat.entity = entity or chat.entity
            chat.is_central = True
            await chat.save()
            return chat
        chat = await Chat.create(telegram_id=telegram_id, title=title, entity=entity, is_central=True)
        return chat

    @staticmethod
    async def remove_central_chat(telegram_id: int) -> bool:
        chat = await Chat.filter(telegram_id=telegram_id).first()
        if chat and chat.is_central:
            chat.is_central = False
            await chat.save()
            return True
        return False