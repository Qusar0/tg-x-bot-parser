import re
import aiohttp
import bleach
import html
from bs4 import BeautifulSoup
from bs4.element import Tag
from app.database.models.Word import Word
from app.database.redis import redis_store


POST_KEY = "post:{id}"


async def is_duplicate(id: str, original_text: str) -> bool:
    original_text = original_text.lower()

    texts = await redis_store.values(POST_KEY.format(id="*"))

    for text in texts:
        if original_text == text:
            return True

    await redis_store.set_value_ex(POST_KEY.format(id=id), original_text, 60 * 60 * 24)
    return False


async def get_fetched_post_ids():
    keys: list[str] = await redis_store.keys(POST_KEY.format(id="*"))
    return [key.split(":")[1] for key in keys]


def is_word_match(text: str, words: list[Word]) -> bool:
    text = text.lower()
    for word in words:
        if word.title in text:
            return True

    return False


async def check_valid_photo(session: aiohttp.ClientSession, photo: str):
    async with session.head(photo) as resp:
        if resp.status == 200:
            return True
        else:
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

    rating = 0
    if chat_id:
        try:
            from app.database.repo.Chat import ChatRepo
            chat = await ChatRepo.get_by_telegram_id(chat_id)
            if chat:
                rating = chat.rating
        except Exception:
            pass

    source_link = soup.new_tag('a', href=chat_link)
    rating_text = f" (⭐{rating})"
    source_link.string = f"🔗 Источник: {chat_title}{rating_text}"

    soup.append("\n\n")
    soup.append(source_link)

    return str(soup)


def remove_links(text: str):
    soup = BeautifulSoup(text, "html.parser")

    for a_tag in soup.find_all("a"):
        a_tag.unwrap()

    text_content = str(soup)

    text_content = re.sub(r'\n\s*\n\s*\n', '\n\n', text_content)
    text_content = re.sub(r'[ \t]+', ' ', text_content)
    text_content = text_content.strip()

    return text_content


def remove_keywords(text: str, keyword):
    """
    Удаляет ключевые слова из текста.
    Работает с HTML разметкой и удаляет слова с учетом границ слов.
    Сохраняет форматирование и переносы строк.
    """
    soup = BeautifulSoup(text, "html.parser")

    for element in soup.find_all(string=True):
        if not element.strip():
            continue

        new_text = element
        kw = keyword.title

        pattern = r'\b' + re.escape(kw) + r'\b[ \t,\.!?;:]*'

        new_text = re.sub(pattern, '', new_text, flags=re.IGNORECASE)

        new_text = re.sub(r'[ \t]+', ' ', new_text)
        new_text = re.sub(r'\n\s+', '\n', new_text)
        new_text = re.sub(r'\s+\n', '\n', new_text)

        element.replace_with(new_text)

    return str(soup)


async def preprocess_text(
    text: str,
    keyword: Word,
    allowed_tags=["a", "b", "i", "u", "s", "em", "code", "stroke", "br", "p"],
    allowed_attrs={"a": ["href"]},
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

    text = remove_links(text)

    from app.database.repo.Word import WordRepo
    from app.enums import WordType
    filter_words = await WordRepo.get_all(WordType.filter_word)
    for filter_word in filter_words:
        text = remove_keywords(text, filter_word)

    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    return text
