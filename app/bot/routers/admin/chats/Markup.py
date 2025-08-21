from pyrogram import types as pyrogram_types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from app.bot.callback_data import (
    back_menu_cb,
    chats_add_cb,
    chats_cb,
    chats_load_from_account,
    chats_remove_cb,
    chats_show_cb,
    delete_cb,
    chats_monitorings_cb,
    chats_central_cb,
    chats_central_add_cb,
    chats_central_remove_cb,
    chats_central_add_me_cb,
    chats_add_loaded_chat_cb,
    ChatsCentralDeleteCb,
    ChooseChatCb,
    NavigationChatCb,
    chats_uploading_cb,
)
from app.settings import settings
from .phrases import cancel_chat_action


class Markup:
    @staticmethod
    def load_from_account() -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()
        markup.row(InlineKeyboardButton(text="💾 Выгрузить с аккаунта", callback_data=chats_load_from_account))
        return markup.as_markup()

    @staticmethod
    def nav_show_chats_from_account(chats: list[pyrogram_types.Chat], page: int = 0) -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()

        start = page * 10
        end = start + 10

        nav_chats = chats[start:end]

        # Добавляем кнопки в клавиатуру
        for chat in nav_chats:
            is_checked = "✅ " if chat.is_choose else "❌ "

            markup.row(
                InlineKeyboardButton(
                    text=f"{is_checked} {chat.title}",
                    callback_data=ChooseChatCb(chat_id=chat.id, is_choose=chat.is_choose, page=page).pack(),
                )
            )

        # Добавляем кнопки навигации "влево" и "вправо"
        nav_buttons = []
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton(text="«", callback_data=NavigationChatCb(direction="left", page=page).pack())
            )

        if end < len(chats):
            nav_buttons.append(
                InlineKeyboardButton(text="»", callback_data=NavigationChatCb(direction="right", page=page).pack())
            )

        markup.row(*nav_buttons)

        markup.row(InlineKeyboardButton(text="Сохранить ☑️", callback_data=chats_add_loaded_chat_cb))

        return markup.as_markup()

    @staticmethod
    def cancel_action() -> InlineKeyboardMarkup:
        markup = ReplyKeyboardBuilder()
        markup.row(KeyboardButton(text=cancel_chat_action))
        return markup.as_markup(resize_keyboard=True)

    @staticmethod
    def remove() -> ReplyKeyboardRemove:
        return ReplyKeyboardRemove()

    @staticmethod
    def back_menu() -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()
        markup.row(InlineKeyboardButton(text="⬅️ Вернуться назад", callback_data=chats_cb))
        return markup.as_markup()

    @staticmethod
    def back_central_chat(is_add: bool = False) -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()

        if is_add and not settings.get_central_chats():
            markup.row(
                InlineKeyboardButton(text="👋 Добавить меня (текущий чат)", callback_data=chats_central_add_me_cb)
            )

        markup.row(InlineKeyboardButton(text="⬅️ Вернуться назад", callback_data=chats_central_cb))
        return markup.as_markup()

    @staticmethod
    def back_monitoring_chat() -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()
        markup.row(InlineKeyboardButton(text="⬅️ Вернуться назад", callback_data=chats_monitorings_cb))
        return markup.as_markup()

    @staticmethod
    def delete_document() -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()
        markup.row(InlineKeyboardButton(text="❌ Убрать файл", callback_data=delete_cb))
        return markup.as_markup()

    @staticmethod
    def open_menu() -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()

        markup.row(InlineKeyboardButton(text="💬 Мониторинг чаты", callback_data=chats_monitorings_cb))
        markup.row(InlineKeyboardButton(text="💬 Чаты для переотправки", callback_data=chats_central_cb))

        markup.row(InlineKeyboardButton(text="⬅️ Вернуться назад", callback_data=back_menu_cb))

        return markup.as_markup()

    @staticmethod
    def monitoring_chats_menu() -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()
        markup.row(
            InlineKeyboardButton(text="➕ Чат", callback_data=chats_add_cb),
            InlineKeyboardButton(text="➖ Чат", callback_data=chats_remove_cb),
        )
        markup.row(
            InlineKeyboardButton(text="💾 Выгрузить с аккаунта", callback_data=chats_load_from_account),
        )
        markup.row(
            InlineKeyboardButton(text="👁️ Список чатов", callback_data=chats_show_cb),
        )
        markup.row(
            InlineKeyboardButton(text="📗 Список чатов excel", callback_data=chats_uploading_cb)
        )
        markup.row(InlineKeyboardButton(text="⬅️ Шаг назад", callback_data=chats_cb))

        return markup.as_markup()

    @staticmethod
    def central_chats_menu() -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()

        markup.row(
            InlineKeyboardButton(text="➕ Чат", callback_data=chats_central_add_cb),
            InlineKeyboardButton(text="➖ Чат", callback_data=chats_central_remove_cb),
        )
        markup.row(InlineKeyboardButton(text="⬅️ Шаг назад", callback_data=chats_cb))

        return markup.as_markup()

    @staticmethod
    def remove_central_chats() -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()

        for chat in settings.get_central_chats():
            markup.row(
                InlineKeyboardButton(
                    text=f"🗑 {chat.title} | {chat.chat_id}",
                    callback_data=ChatsCentralDeleteCb(chat_id=chat.chat_id).pack(),
                )
            )

        markup.row(InlineKeyboardButton(text="⬅️ Шаг назад", callback_data=chats_central_cb))

        return markup.as_markup()
