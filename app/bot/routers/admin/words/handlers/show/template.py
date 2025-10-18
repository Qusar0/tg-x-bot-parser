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

    # Определяем название и платформу
    is_keyword = word_type in [WordType.tg_keyword, WordType.x_keyword]
    is_stopword = word_type in [WordType.tg_stopword, WordType.x_stopword]
    is_filter_word = word_type in [WordType.tg_filter_word, WordType.x_filter_word]
    
    platform = "TG" if word_type.value.startswith("tg_") else "X"
    
    if is_keyword:
        raw_template += f"🔑 Список ключ-слов {platform}:\n"
        html_template += f"<b><u>🔑 Список ключ-слов {platform}:</u></b>\n"
        raw_words, formatted_words = await format_words(words)
        raw_template += raw_words
        html_template += formatted_words

    elif is_stopword:
        raw_template += f"🛑 Список стоп-слов {platform}:\n"
        html_template += f"<b>🛑 Список стоп-слов {platform}:</b>\n"
        raw_words, formatted_words = await format_words(words)
        raw_template += raw_words
        html_template += formatted_words

    elif is_filter_word:
        raw_template += f"🔍 Список фильтр-слов {platform}:\n"
        html_template += f"<b>🔍 Список фильтр-слов {platform}:</b>\n"
        raw_words, formatted_words = await format_words(words)
        raw_template += raw_words
        html_template += formatted_words

    return raw_template, html_template
