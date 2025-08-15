import bleach
import html
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


def preprocess_text(
    text: str,
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

    return text
