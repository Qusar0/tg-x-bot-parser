from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.bot.callback_data import chats_cb, tg_parser_cb, x_parser_cb, x_channels_cb


class Markup:
    @staticmethod
    def open_menu() -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()

        markup.row(
            InlineKeyboardButton(text="📱 Парсер Telegram", callback_data=tg_parser_cb),
            InlineKeyboardButton(text="🐦 Парсер X (Twitter)", callback_data=x_parser_cb),
        )

        markup.row(
            InlineKeyboardButton(text="💬 Чаты", callback_data=chats_cb),
            InlineKeyboardButton(text="🔗 X каналы", callback_data=x_channels_cb),
        )

        return markup.as_markup()
