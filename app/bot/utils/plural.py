from enum import StrEnum, auto


class PluralType(StrEnum):
    stopword = auto()
    word = auto()
    user = auto()


def get_plural_hash_map():
    return {
        PluralType.stopword.name: ("стоп-слово", "стоп-слова", "стоп-слов"),
        PluralType.word.name: ("слово", "слова", "слов"),
        PluralType.user.name: ("пользователь", "пользователя", "пользователей"),
    }


def plural_value(number: int, plural_type: PluralType):
    plural_hash_map = get_plural_hash_map()
    number = int(number)
    if number % 10 == 1 and number % 100 != 11:
        return str(number) + f" {plural_hash_map[plural_type.name][0]}"
    elif number % 10 in [2, 3, 4] and number % 100 not in [12, 13, 14]:
        return str(number) + f" {plural_hash_map[plural_type.name][1]}"
    else:
        return str(number) + f" {plural_hash_map[plural_type.name][2]}"
