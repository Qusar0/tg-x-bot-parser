from typing import Optional

from app.database.repo.Word import WordRepo
from app.database.models.Word import Word
from app.enums import WordType


def is_word_contains(text: str, word: Word) -> bool:
    # text приходит уже в нижнем регистре, приводим и токены слова,
    # чтобы ключи с заглавными буквами (например, из Excel) тоже матчились
    for token in word.title.lower().split():
        if token not in text:
            return False

    return True


def get_matched_words(text: str, words: list[Word]) -> list[Word]:
    matched_words = []
    text = text.lower()

    for word in words:
        if is_word_contains(text, word):
            matched_words.append(word)

    return matched_words


async def is_word_match(text: str, word_type: WordType, central_chat_id: Optional[int] = None) -> list[Word]:
    if central_chat_id:
        words = await WordRepo.get_all_from_central_id(word_type, central_chat_id)
    else:
        words = await WordRepo.get_all(word_type)
    matched_words = get_matched_words(text, words)

    return matched_words
