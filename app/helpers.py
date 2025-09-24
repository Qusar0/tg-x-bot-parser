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


def add_source_link(text: str, header: Tag):
    soup = BeautifulSoup(text, 'html.parser')
    channel_name = header.get_text().strip()
    link = header.get("href")

    if '@' in link:
        link = link.split("@")[-1]
        link.rstrip('/')
        link = f"https://t.me/{link}"

    source_link = soup.new_tag('a', href=link)
    source_link.string = f"🔗 Источник: {channel_name}"

    soup.append("\n\n")
    soup.append(source_link)

    return str(soup)


def remove_links(text: str):
    soup = BeautifulSoup(text, "html.parser")

    for a_tag in soup.find_all("a"):
        link_text = a_tag.get_text()
        if is_url(link_text) or is_at(link_text):
            a_tag.decompose()
        else:
            a_tag.unwrap()

    return str(soup)


def remove_keywords(text: str, keyword):
    soup = BeautifulSoup(text, "html.parser")

    for element in soup.find_all(string=True):
        new_text = element
        kw = keyword.title
        new_text = re.sub(
            r'\b' + re.escape(kw) + r'\b[ \t]*',
            '',
            new_text,
            flags=re.IGNORECASE
        )
        element.replace_with(new_text)

    return str(soup)


def preprocess_text(
    text: str,
    keyword: Word,
    allowed_tags=["a", "b", "i", "u", "s", "em", "code", "stroke"],
    allowed_attrs={"a": ["href"]},
) -> str:
    text = text.replace("<br/>", "\n").replace("<br>", "\n")  # .replace("&nbsp", " ")
    text = html.unescape(text)

    text = bleach.clean(
        text,
        tags=allowed_tags,
        attributes=allowed_attrs,
        strip=True,
    )

    text = remove_keywords(remove_links(text), keyword)

    return text
