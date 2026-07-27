from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.bot.callback_data import back_menu_cb, WordMenuCb, ChangeSettingsCb, x_channels_choose_winrate
from app.enums import WordType
from app.settings import settings


class Markup:
    @staticmethod
    def open_menu() -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()

        try:
            enabled = bool(settings.get_source_x())
        except Exception:
            enabled = True

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

        circle = "🟢" if enabled else "🔴"
        toggle_cb = ChangeSettingsCb(field="source_x", value=not enabled).pack()
        markup.row(
            InlineKeyboardButton(
                text=f"Указание источника: {circle}",
                callback_data=toggle_cb,
            ),
        )

        markup.row(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=back_menu_cb),
        )

        return markup.as_markup()
    
    @staticmethod
    def cancel_input(back_callback) -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()
        markup.row(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=back_callback),
        )

        return markup.as_markup()
