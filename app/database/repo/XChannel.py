from app.database.models import XChannel


class XChannelRepo:
    @staticmethod
    async def get_all() -> list[XChannel]:
        channels = await XChannel.all()
        return channels

    @staticmethod
    async def add(title: str, url: str, central_chat_id: int = None) -> XChannel:
        channel = await XChannel.create(title=title, url=url, central_chat_id=central_chat_id)
        return channel

    @staticmethod
    async def delete(channel_id: int) -> bool:
        channel = await XChannel.filter(id=channel_id).first()
        if channel:
            await channel.delete()
            return True
        return False

    @staticmethod
    async def get_by_id(channel_id: int) -> XChannel | None:
        channel = await XChannel.filter(id=channel_id).first()
        return channel

    @staticmethod
    async def get_by_url(url: str) -> XChannel | None:
        channel = await XChannel.filter(url=url).first()
        return channel

    @staticmethod
    async def get_by_title(title: str) -> XChannel | None:
        """Поиск канала по названию (без учета регистра)"""
        channel = await XChannel.filter(title__icontains=title).first()
        return channel

    @staticmethod
    async def get_by_rating(rating: int) -> list[XChannel]:
        """Получить каналы по рейтингу"""
        channels = await XChannel.filter(rating=rating).all()
        return channels

    @staticmethod
    async def get_by_rating_greater_than(min_rating: int) -> list[XChannel]:
        """Получить каналы с рейтингом больше указанного"""
        channels = await XChannel.filter(rating__gt=min_rating).all()
        return channels

    @staticmethod
    async def update_rating(channel_id: int, rating: int) -> bool:
        """Обновить рейтинг канала"""
        channel = await XChannel.filter(id=channel_id).first()
        if channel:
            channel.rating = rating
            await channel.save()
            return True
        return False

