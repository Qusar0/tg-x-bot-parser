from app.enums import WordType
from app.database.models import Word
from loguru import logger


class WordRepo:
    @staticmethod
    async def get_all(word_type: WordType) -> list[Word]:
        words = await Word.filter(word_type=word_type).all()
        return words

    @staticmethod
    async def get_one(title: str, word_type: WordType) -> Word | None:
        word = await Word.filter(title=title, word_type=word_type).first()
        return word

    @staticmethod
    async def add_many(titles: list[str], word_type: WordType, central_chat_id: int) -> list[Word]:
        added_words = []
        for title in titles:
            try:
                if not await WordRepo.get_one(title, word_type):
                    word = await Word.create(
                        title=title,
                        normalized_title=title,
                        word_type=word_type,
                        central_chat_id=central_chat_id,
                    )
                    added_words.append(word)
            except Exception as ex:
                logger.warning(ex)

        return added_words

    @staticmethod
    async def delete_many(titles: list[str], word_type: WordType) -> list[str]:
        deleted_words = []
        for title in titles:
            candidate = await Word.filter(title=title, word_type=word_type).first()

            if candidate:
                await candidate.delete()
                deleted_words.append(candidate.title)

        return deleted_words

    @staticmethod
    async def bulk_delete(words: list[Word]) -> int:
        deleted_count = 0
        for word in words:
            try:
                await word.delete()
                deleted_count += 1
            except Exception:
                pass

        return deleted_count

    @staticmethod
    async def get_by_platform(word_type: WordType, central_chat_id: int = None) -> list[Word]:
        """Получить слова по платформе и опционально по чату"""
        query = Word.filter(word_type=word_type)
        if central_chat_id:
            query = query.filter(central_chat_id=central_chat_id)
        return await query.all()

    @staticmethod
    async def get_platform_stats() -> dict:
        """Получить статистику по платформам"""
        stats = {}
        for word_type in WordType:
            count = await Word.filter(word_type=word_type).count()
            stats[word_type.value] = count
        return stats