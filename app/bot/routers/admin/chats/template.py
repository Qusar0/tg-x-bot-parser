from app.database.models.Chat import Chat


def get_loaded_chats_template(chats: list[Chat]) -> tuple[str, str]:
    raw_template = "✅ Выгрузили новые чаты с аккаунта:\n"
    html_template = "✅ <b>Выгрузили новые чаты с аккаунта\n</b>"

    for num, chat in enumerate(chats, start=1):
        raw_template += f"{num}. {chat.title} | {chat.link if hasattr(chat, 'link') else chat.telegram_id}\n"
        html_template += f"{num}. <a href='{chat.link}'>{chat.title}</a>\n"

    return raw_template, html_template


def get_chats_template(chats: list[Chat]) -> tuple[str, str]:
    raw_template = "💬 Список чатов:\n"
    html_template = "<b>💬 Список чатов:</b>\n"

    for num, chat in enumerate(chats, start=1):
        raw_template += f"{num}. {chat.title} | {chat.link if getattr(chat, 'link') else chat.telegram_id} [{chat.formatted_created_at}]\n"   # noqa: E501
        html_template += f"{num}. <a href='{chat.link if getattr(chat, 'link') else ''}'>{chat.title}</a> <code>[{chat.formatted_created_at}]</code>\n"   # noqa: E501

    return raw_template, html_template
