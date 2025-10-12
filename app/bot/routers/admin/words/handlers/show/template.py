from app.database.models.Word import Word
from app.database.repo.Chat import ChatRepo
from app.enums import WordType


async def format_words(words: list[Word]) -> tuple[str, str]:
    formatted_text = ""
    raw_text = ""

    if not words:
        formatted_text = "<code>Еще не добавлены</code>"
        raw_text = "Еще не добавлены"
    else:
        central_chats = await ChatRepo.get_central_chats()
        chat_dict = {chat.telegram_id: chat.title for chat in central_chats}

        for num, word in enumerate(words, start=1):
            chat_name = chat_dict.get(word.central_chat_id, f"ID:{word.central_chat_id}")

            formatted_text += f"{num}. {word.title} <code>[{chat_name}]</code>\n"
            raw_text += f"{num}. {word.title} [{chat_name}]\n"

    return raw_text, formatted_text


async def get_words_template(words: list[Word], word_type: WordType) -> tuple[str, str]:
    raw_template = ""
    html_template = ""

    if word_type == WordType.keyword:
        raw_template += "🔑 Список ключ-слов:\n"
        html_template += "<b><u>🔑 Список ключ-слов:</u></b>\n"
        raw_words, formatted_words = await format_words(words)
        raw_template += raw_words
        html_template += formatted_words

    elif word_type == WordType.stopword:
        raw_template += "🛑 Список стоп-слов:\n"
        html_template += "<b>🛑 Список стоп-слов:</b>\n"
        raw_words, formatted_words = await format_words(words)
        raw_template += raw_words
        html_template += formatted_words

    elif word_type == WordType.filter_word:
        raw_template += "🔍 Список фильтр-слов:\n"
        html_template += "<b>🔍 Список фильтр-слов:</b>\n"
        raw_words, formatted_words = await format_words(words)
        raw_template += raw_words
        html_template += formatted_words

    return raw_template, html_template
