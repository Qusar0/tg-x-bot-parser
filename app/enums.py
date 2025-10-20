from enum import StrEnum


class WordType(StrEnum):
    # Telegram слова
    tg_keyword = "tg_keyword"
    tg_stopword = "tg_stopword"
    tg_filter_word = "tg_filter_word"
    
    # X слова
    x_keyword = "x_keyword"
    x_stopword = "x_stopword"
    x_filter_word = "x_filter_word"
