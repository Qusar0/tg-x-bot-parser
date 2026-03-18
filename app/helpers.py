import re
import aiohttp
import bleach
import html
from typing import Optional
from bs4 import BeautifulSoup
from bs4.element import Tag
from app.database.models.Word import Word
from app.database.redis import redis_store
from app.settings import settings

POST_KEY = "post:{chat}:{id}"


async def is_duplicate(id: str, original_text: str, chat_id: int | None = None) -> bool:
    original_text = original_text.lower()
    from loguru import logger

    try:
        chat_key = chat_id if chat_id is not None else "global"
        key = POST_KEY.format(chat=chat_key, id=id)

        # 1. Быстрая проверка: уже есть запись с таким ID
        # Если мы уже когда‑то обрабатывали этот твит (ID уникален),
        # то независимо от изменений текста считаем его дубликатом.
        existing_by_id = await redis_store.get_value(key)
        if existing_by_id is not None:
            logger.info(f"Найден дубликат по ID в Redis: {id}")
            return True

        # Сначала проверяем, есть ли уже такой текст в Redis
        # Используем более эффективный подход - проверяем только недавние посты
        recent_keys = await redis_store.keys(f"post:{chat_key}:*")
        
        if recent_keys:
            # Ограничиваем количество проверяемых ключей для производительности
            max_check_keys = 100
            if len(recent_keys) > max_check_keys:
                # Берем только последние ключи (предполагаем, что они отсортированы)
                recent_keys = recent_keys[-max_check_keys:]
            
            # Получаем значения только для выбранных ключей
            texts = await redis_store.redis.mget(recent_keys) if recent_keys else []
            
            logger.info(
                f"Проверяем дубликаты для ID: {id}, "
                f"проверяем {len(texts)} из "
                f"{len(await redis_store.keys(POST_KEY.format(chat=chat_key, id='*')))} текстов в Redis"
            )
            
            # Проверяем, что texts не None и не пустой
            if texts:
                for i, text in enumerate(texts):
                    if text and original_text == text:
                        logger.info(f"Найден дубликат! ID: {id}, совпадение с текстом #{i}")
                        return True

        # Сохраняем новый пост с TTL 24 часа
        # В XScrapper мы рассматриваем посты возрастом до 24 часов (см. parse_posts),
        # поэтому, чтобы один и тот же твит не пересылался повторно в течение суток,
        # TTL должен быть не меньше этого окна.
        ttl_seconds = 60 * 60 * 24
        await redis_store.set_value_ex(key, original_text, ttl_seconds)
        logger.info(f"Сохраняем новый пост в Redis: {id} (chat={chat_key}) (TTL: 24 часа)")
        return False
    except Exception as e:
        # Если Redis недоступен, логируем ошибку и продолжаем без проверки дубликатов
        logger.error(f"Ошибка при проверке дубликатов: {e}")
        return False


async def get_fetched_post_ids(chat_id: int | None = None):
    chat_key = chat_id if chat_id is not None else "global"
    keys: list[str] = await redis_store.keys(f"post:{chat_key}:*")
    return [key.split(":")[2] for key in keys]


async def cleanup_old_redis_data():
    """Очищает старые данные из Redis для предотвращения переполнения памяти"""
    from loguru import logger
    
    try:
        # Очищаем старые посты (старше 2 часов)
        deleted_posts = await redis_store.cleanup_old_posts(max_age_hours=2)
        
        # Получаем информацию об использовании памяти
        memory_info = await redis_store.get_memory_usage()
        
        logger.info(f"[CLEANUP] Очистка Redis завершена:")
        logger.info(f"[CLEANUP] - Удалено постов: {deleted_posts}")
        logger.info(f"[CLEANUP] - Использовано памяти: {memory_info.get('used_memory_human', 'N/A')}")
        logger.info(f"[CLEANUP] - Количество ключей: {memory_info.get('keys_count', 'N/A')}")
        
        return deleted_posts
    except Exception as e:
        logger.error(f"[CLEANUP] Ошибка при очистке Redis: {e}")
        return 0


def is_word_match(text: str, words: list[Word]) -> bool:
    text = text.lower()
    for word in words:
        if word.title in text:
            return True

    return False


async def check_valid_photo(session: aiohttp.ClientSession, photo: str):
    try:
        async with session.get(photo, allow_redirects=True) as resp:
            return 200 <= resp.status < 400 and resp.content_type.startswith("image")
    except Exception:
        return False


def is_url(string: str):
    url_pattern = re.compile(
        r'^(https?://)?'
        r'([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}'
        r'(:[0-9]{1,5})?'
        r'(/\S*)?$'
    )

    return bool(url_pattern.match(string.strip()))


def is_at(string: str):
    return True if string.startswith("@") else False


def is_source_link(link_text: str) -> bool:
    """
    Определяет, является ли ссылка источником.
    Проверяет различные форматы указания источника.
    """
    link_text = link_text.strip().lower()

    source_patterns = [
        "🔗 источник:",
        "источник:",
        "source:",
        "источник",
    ]

    for pattern in source_patterns:
        if link_text.startswith(pattern):
            return True

    for pattern in source_patterns:
        if pattern in link_text:
            return True

    return False


async def add_source_link(text: str, header: Tag):
    soup = BeautifulSoup(text, 'html.parser')
    channel_name = header.get_text().strip()
    link = header.get("href")

    entity = None
    if link:
        if '@' in link:
            entity = link.split("@")[-1]
        elif 't.me/' in link:
            after = link.split('t.me/')[-1]
            entity = after.split('/')[0]
        if entity:
            entity = entity.strip().strip('/')
            link = f"https://t.me/{entity}"

    source_link = soup.new_tag('a', href=link)
    source_link.string = f"🔗 Источник: {channel_name}"

    soup.append("\n\n")
    soup.append(source_link)

    return str(soup)


async def add_x_link(text: str, link: str, channel_rating: int = 0, channel_winrate: float = 0):
    soup = BeautifulSoup(text, 'html.parser')
    # link приходит как "/username/status/123..." — нормализуем
    normalized = link.lstrip('/')
    account_name = normalized.split('/')[0]
    link = f"https://x.com/{normalized}"
    
    # Добавляем рейтинг (всегда)
    rating_text = f"⭐{channel_rating}" if channel_rating > 0 else "❌"
    rating_element = soup.new_string(f"Rating: {rating_text}\n")
    soup.append("\n\n")
    soup.append(rating_element)
    soup.append("\n")
    winrate_text = f"{channel_winrate}%" if channel_winrate > 0 else "❌"
    winrate_element = soup.new_string(f"Winrate: {winrate_text}\n")
    soup.append(winrate_element)
    soup.append("\n")
    # Добавляем источник только если включена настройка
    try:
        if settings.get_source_x():
            source_link = soup.new_tag('a', href=link)
            source_link.string = f"🔗 Источник: {account_name}"
            soup.append(source_link)
    except Exception:
        # Если настройка недоступна, добавляем источник по умолчанию
        source_link = soup.new_tag('a', href=link)
        source_link.string = f"🔗 Источник: {account_name}"
        soup.append(source_link)

    return str(soup)


async def add_userbot_source_link(text: str, chat_title: str, chat_link: str, chat_id: int = None):
    """
    Добавляет источник к тексту для юзербота.
    Если источник уже есть в тексте, ничего не добавляет.
    """

    soup = BeautifulSoup(text, 'html.parser')

    text_lower = text.lower()
    source_patterns = ["🔗 источник:", "источник:", "source:", "источник"]

    for pattern in source_patterns:
        if pattern in text_lower:
            return text

    # Получаем рейтинг и винрейт (всегда)
    rating = 0
    winrate = 0
    if chat_id:
        try:
            from app.database.repo.Chat import ChatRepo
            chat = await ChatRepo.get_by_telegram_id(chat_id)
            if chat:
                rating = chat.rating
                winrate = chat.winrate
        except Exception:
            pass

    # Добавляем рейтинг (всегда)
    rating_text = f"⭐{rating}" if rating > 0 else "❌"
    rating_element = soup.new_string(f"Rating: {rating_text}\n")

    winrate_text = f"{winrate}%" if winrate > 0 else "❌"
    winrate_element = soup.new_string(f"Winrate: {winrate_text}\n")

    soup.append("\n\n")
    soup.append(rating_element)
    soup.append("\n")
    soup.append(winrate_element)
    soup.append("\n")

    # Добавляем источник только если включена настройка
    try:
        if settings.get_source_tg():
            source_link = soup.new_tag('a', href=chat_link)
            source_link.string = f"🔗 Источник: {chat_title}"
            soup.append(source_link)
    except Exception:
        # Если настройка недоступна, добавляем источник по умолчанию
        source_link = soup.new_tag('a', href=chat_link)
        source_link.string = f"🔗 Источник: {chat_title}"
        soup.append(source_link)

    return str(soup)


def remove_links(text: str):
    """Удаляет теги ссылок и голые URL-ы из текста."""
    soup = BeautifulSoup(text, "html.parser")

    # 1) Полностью удаляем все теги <a>
    for a_tag in soup.find_all("a"):
        a_tag.decompose()

    text_content = str(soup)

    # 2) Удаляем голые URL-ы (http/https, а также домены без схемы)
    url_regex = r"(https?://\S+|(?:www\.)?[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/\S*)?)"
    text_content = re.sub(url_regex, "", text_content)

    # 3) Чистим лишние пробелы/переносы
    text_content = re.sub(r'\n\s*\n\s*\n', '\n\n', text_content)
    text_content = re.sub(r'[ \t]+', ' ', text_content)
    text_content = text_content.strip()

    return text_content


def remove_keywords(text: str, keyword):
    """
    Удаляет ключевые слова из текста.
    Работает с HTML разметкой и удаляет слова с учетом границ слов.
    Сохраняет форматирование и переносы строк.
    Корректно обрабатывает смайлики и спецсимволы.
    """
    soup = BeautifulSoup(text, "html.parser")

    # Получаем ключевое слово как строку
    kw = keyword if isinstance(keyword, str) else keyword.title

    # Экранируем спецсимволы в ключевом слове
    escaped_kw = re.escape(kw)

    # Паттерн для поиска слова с границами слов
    # Используем negative lookbehind и lookahead для Unicode символов
    pattern = r'(?<!\w)' + escaped_kw + r'(?!\w)'

    for element in soup.find_all(string=True):
        if not element.strip():
            continue

        original_text = element

        # Удаляем ключевое слово
        new_text = re.sub(pattern, '', original_text, flags=re.UNICODE | re.IGNORECASE)

        # Удаляем возможные пробелы после удаленного слова
        new_text = re.sub(r' +', ' ', new_text)  # множественные пробелы -> один пробел
        new_text = re.sub(r'\n\s+', '\n', new_text)  # пробелы после переноса строки
        new_text = re.sub(r'\s+\n', '\n', new_text)  # пробелы перед переносом строки
        new_text = re.sub(r'[ \t]+$', '', new_text, flags=re.MULTILINE)  # пробелы в конце строк

        # Если текст изменился, заменяем его
        if new_text != original_text:
            element.replace_with(new_text)

    return str(soup)


async def preprocess_text(
    text: str,
    keyword: Word,
    allowed_tags=["a", "b", "i", "u", "s", "em", "code", "stroke", "br", "p"],
    allowed_attrs={"a": ["href"]},
    platform: str = "tg",  # "tg" или "x"
    central_chat_id: Optional[int] = None,  # Если есть централ чат берем фильтр слова по нему
) -> str:
    text = text.replace("<br/>", "\n").replace("<br>", "\n")
    text = text.replace("</p>", "\n").replace("<p>", "")
    text = html.unescape(text)

    text = bleach.clean(
        text,
        tags=allowed_tags,
        attributes=allowed_attrs,
        strip=True,
    )

    # Удаляем все ссылки (теги и голые URL-ы)
    text = remove_links(text)

    from app.database.repo.Word import WordRepo
    from app.enums import WordType

    # Выбираем фильтр-слова в зависимости от платформы
    if platform == "tg":
        if central_chat_id:
            filter_words = await WordRepo.get_all_from_central_id(WordType.tg_filter_word, central_chat_id)
        else:
            filter_words = await WordRepo.get_all(WordType.tg_filter_word)
    else:  # x
        filter_words = await WordRepo.get_all(WordType.x_filter_word)

    for filter_word in filter_words:
        text = remove_keywords(text, filter_word)

    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    return text
