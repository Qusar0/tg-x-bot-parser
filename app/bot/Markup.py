from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.bot.callback_data import chats_cb, WordMenuCb
from app.enums import WordType


class Markup:
    @staticmethod
    def open_menu() -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()

        # markup.row(
        #     InlineKeyboardButton(text="⚙️ Настройки", callback_data=settings_cb),
        # )
        markup.row(
            InlineKeyboardButton(text="🔑 Ключ-слова", callback_data=WordMenuCb(word_type=WordType.keyword).pack()),
            InlineKeyboardButton(text="🛑 Стоп-слова", callback_data=WordMenuCb(word_type=WordType.stopword).pack()),
        )

        markup.row(
            InlineKeyboardButton(text="💬 Чаты", callback_data=chats_cb),
        )

        return markup.as_markup()
