import re
import aiohttp
import bleach
import html
from bs4 import BeautifulSoup
from app.database.models.Word import Word
from app.database.redis import redis_store

POST_KEY = "post:{id}"

DOMAINS = {
    "t.me", "telegram.org",
    "vk.com", "instagram.com",
    "x.com", "facebook.com",
    "youtube.com", "tiktok.com",
}


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


def remove_social_links(text: str):
    soup = BeautifulSoup(text, "html.parser")

    for a_tag in soup.find_all("a"):
        href = a_tag.get("href")
        if any(domain in href for domain in DOMAINS):
            a_tag.decompose()

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

    text = remove_keywords(remove_social_links(text), keyword)

    return text
