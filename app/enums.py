from enum import StrEnum


class WordType(StrEnum):
    keyword = "keyword"
    stopword = "stopword"
    filter_word = "filter_word"
