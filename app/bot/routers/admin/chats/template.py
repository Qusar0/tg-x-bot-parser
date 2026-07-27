from app.database.models.Chat import Chat


def get_loaded_chats_template(chats: list[Chat]) -> tuple[str, str]:
    raw_template = "✅ Выгрузили новые чаты с аккаунта:\n"
    html_template = "✅ <b>Выгрузили новые чаты с аккаунта\n</b>"

    for num, chat in enumerate(chats, start=1):
        raw_template += f"{num}. {chat.title} | {chat.link if hasattr(chat, 'link') else chat.telegram_id}\n"
        html_template += f"{num}. <a href='{chat.link}'>{chat.title}</a>\n"

    return raw_template, html_template


def get_chats_template(
    chats: list[Chat],
    central_map: dict[int, Chat] | None = None,
    start_index: int = 0,
) -> tuple[str, str]:
    """
    Формируем шаблон списка чатов для мониторинга.
    Если указан central_map, добавляем информацию о привязанном центральном чате.
    """
    raw_template = "💬 Список чатов:\n"
    html_template = "<b>💬 Список чатов:</b>\n"

    central_map = central_map or {}

    for num, chat in enumerate(chats, start=start_index + 1):
        central_chat = central_map.get(chat.central_chat_id)
        if central_chat:
            central_link = getattr(central_chat, "link", None)
            if central_link:
                central_raw = f" | Central: {central_chat.title}"
                central_html = f" | Central: <a href='{central_link}'>{central_chat.title}</a>"
            else:
                central_raw = f" | Central: {central_chat.title}"
                central_html = f" | Central: {central_chat.title}"
        else:
            central_raw = " | Central: ❌"
            central_html = " | Central: ❌"

        self_link = getattr(chat, "link", None)
        if self_link:
            self_html = f"<a href='{self_link}'>{chat.title}</a>"
            self_raw = chat.title
        else:
            self_html = chat.title
            self_raw = chat.title

        raw_template += (
            f"{num}. {self_raw}"
            f"{central_raw} [{chat.formatted_created_at}]\n"
        )
        html_template += (
            f"{num}. {self_html}"
            f"{central_html} "
            f"<code>[{chat.formatted_created_at}]</code>\n"
        )

    return raw_template, html_template
