from app.database.repo.Word import WordRepo
from app.database.models.Word import Word
from app.enums import WordType


def is_word_contains(text: str, word: Word) -> bool:
    is_match = True

    for word in word.title.split():
        if word not in text:
            return False

    return is_match


def get_matched_words(text: str, words: list[Word]) -> list[Word]:
    matched_words = []
    text = text.lower()

    for word in words:
        if is_word_contains(text, word):
            matched_words.append(word)

    return matched_words


async def is_word_match(text: str, word_type: WordType) -> list[Word]:
    words = await WordRepo.get_all(word_type)
    matched_words = get_matched_words(text, words)

    return matched_words
