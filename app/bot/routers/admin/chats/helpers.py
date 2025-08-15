import re

USERNAME_RE = re.compile("@|(?:https?://)?(?:www\\.)?(?:telegram\\.(?:me|dog)|t\\.me)/(@|\\+|joinchat/)?")
VALID_USERNAME_RE = re.compile("^[a-z](?:(?!__)\\w){1,30}[a-z\\d]$", re.IGNORECASE)


def extract_chat_entities(text: str) -> list[str]:
    usernames = set()
    for username in text.split("\n"):
        username = username.strip()
        match = USERNAME_RE.match(username)
        if match:
            matched_username = username[match.end() :]
            is_invite = bool(match.group(1))
            if is_invite:
                usernames.add(username)
            else:
                username = matched_username.rstrip("/")

    if VALID_USERNAME_RE.match(username):
        usernames.add("@" + username.lower())

    return list(usernames)
