from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.bot.callback_data import back_menu_cb, WordMenuCb
from app.enums import WordType


class Markup:
    @staticmethod
    def open_menu() -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()

        markup.row(
            InlineKeyboardButton(
                text="🔑 Ключ-слова X", 
                callback_data=WordMenuCb(word_type=WordType.x_keyword).pack()
            ),
            InlineKeyboardButton(
                text="🛑 Стоп-слова X", 
                callback_data=WordMenuCb(word_type=WordType.x_stopword).pack()
            ),
        )
        markup.row(
            InlineKeyboardButton(
                text="🔍 Фильтр-слова X", 
                callback_data=WordMenuCb(word_type=WordType.x_filter_word).pack()
            ),
        )

        markup.row(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=back_menu_cb),
        )

        return markup.as_markup()
