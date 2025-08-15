from app.database.models.Word import Word
from app.enums import WordType


def format_words(words: list[Word]) -> tuple[str, str]:
    formatted_text = ""
    raw_text = ""

    if not words:
        formatted_text = "<code>Еще не добавлены</code>"
        raw_text = "Еще не добавлены"
    else:
        for num, word in enumerate(words, start=1):
            formatted_text += f"{num}. {word.title} <code>[{word.formatted_created_at}]</code>\n"
            raw_text += f"{num}. {word.title} [{word.formatted_created_at}]\n"

    return raw_text, formatted_text


def get_words_template(words: list[Word], word_type: WordType) -> tuple[str, str]:
    raw_template = ""
    html_template = ""

    if word_type == WordType.keyword:
        raw_template += "🔑 Список ключ-слов:\n"
        html_template += "<b><u>🔑 Список ключ-слов:</u></b>\n"
        raw_words, formatted_words = format_words(words)
        raw_template += raw_words
        html_template += formatted_words

    elif word_type == WordType.stopword:
        raw_template += "🛑 Список стоп-слов:\n"
        html_template += "<b>🛑 Список стоп-слов:</b>\n"
        raw_words, formatted_words = format_words(words)
        raw_template += raw_words
        html_template += formatted_words

    return raw_template, html_template
