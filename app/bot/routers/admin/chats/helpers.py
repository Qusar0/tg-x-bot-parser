import re

USERNAME_RE = re.compile("@|(?:https?://)?(?:www\\.)?(?:telegram\\.(?:me|dog)|t\\.me)/(@|\\+|joinchat/)?")
VALID_USERNAME_RE = re.compile("^[a-z](?:(?!__)\\w){1,30}[a-z\\d]$", re.IGNORECASE)


def extract_chat_entities(text: str) -> list[str]:
    usernames = set()
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        match = USERNAME_RE.match(line)
        if match:
            matched_username = line[match.end():]
            is_invite = bool(match.group(1))
            if is_invite:
                usernames.add(line)
            else:
                username = matched_username.rstrip("/")
                if VALID_USERNAME_RE.match(username):
                    usernames.add("@" + username.lower())
        else:
            if line.startswith("@"):
                username = line[1:].rstrip("/")
                if VALID_USERNAME_RE.match(username):
                    usernames.add("@" + username.lower())
            elif line.startswith("https://t.me/") or line.startswith("http://t.me/"):
                username = line.split("/")[-1].rstrip("/")
                if VALID_USERNAME_RE.match(username):
                    usernames.add("@" + username.lower())
            elif line.startswith("t.me/"):
                username = line.split("/")[-1].rstrip("/")
                if VALID_USERNAME_RE.match(username):
                    usernames.add("@" + username.lower())

    return list(usernames)


import re

def extract_first_float(text):
    pattern = r'\b\d+(?:[.,]\d{1,2})?\b|(?<!\d)[.,]\d{1,2}\b'
    
    matches = re.findall(pattern, text)
    
    if not matches:
        return False
    
    for match in matches:
        try:
            # Обрабатываем случаи типа ".5" или ",5"
            if match.startswith('.') or match.startswith(','):
                normalized = '0' + match.replace(',', '.')
            else:
                normalized = match.replace(',', '.')
            
            num = float(normalized)
            
            if num < 100:
                return num
        except ValueError:
            continue
    
    return False