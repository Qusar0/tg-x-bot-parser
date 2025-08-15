def extract_words(words_str: str) -> list[str]:
    """Извлекаем слова с новой строчки и через запятую"""
    words = set()

    for line in words_str.splitlines():
        line = line.strip().lower()
        if not line:
            continue

        for key in line.split(","):
            words.add(key.strip())

    return sorted(list(words))
