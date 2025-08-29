from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.enums import WordType
from app.settings import settings
from app.bot.callback_data import (
    back_menu_cb,
    ChooseCentralChatForWordCb,
    DeleteAllWordsCb,
    WordMenuAddCb,
    WordMenuCb,
    WordMenuDeleteCb,
    WordShowCb,
    WordUploadingCb,
)


class Markup:
    @staticmethod
    def back_menu(word_type: WordType) -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()
        markup.row(InlineKeyboardButton(text="⬅️ Вернуться назад", callback_data=WordMenuCb(word_type=word_type).pack()))
        return markup.as_markup()

    @staticmethod
    def choose_central_chat(word_type: WordType) -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()

        for chat in settings.get_central_chats():
            markup.row(
                InlineKeyboardButton(
                    text=chat.title,
                    callback_data=ChooseCentralChatForWordCb(word_type=word_type, chat_id=chat.chat_id).pack(),
                )
            )

        markup.row(InlineKeyboardButton(text="« Назад", callback_data=WordMenuCb(word_type=WordType.keyword).pack()))

        return markup.as_markup()

    @staticmethod
    def delete_all_words(word_type: WordType) -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()

        if word_type == WordType.stopword:
            text = "❌ Удалить все стоп-слова"
        elif word_type == WordType.keyword:
            text = "❌ Удалить все ключ-слова"

        markup.row(
            InlineKeyboardButton(
                text=text,
                callback_data=DeleteAllWordsCb(word_type=word_type).pack(),
            )
        )
        markup.row(InlineKeyboardButton(text="⬅️ Вернуться назад", callback_data=WordMenuCb(word_type=word_type).pack()))
        return markup.as_markup()

    @staticmethod
    def cancel_action() -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()
        markup.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action"))
        return markup.as_markup()

    @staticmethod
    def open_menu(word_type: WordType) -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()

        if word_type == WordType.keyword:
            markup.row(
                InlineKeyboardButton(
                    text="➕ Ключ-слова",
                    callback_data=WordMenuAddCb(word_type=WordType.keyword).pack(),
                ),
                InlineKeyboardButton(
                    text="➖ Ключ-слова",
                    callback_data=WordMenuDeleteCb(word_type=WordType.keyword).pack(),
                ),
            )
            markup.row(
                InlineKeyboardButton(
                    text="👁️ Список ключ-слов",
                    callback_data=WordShowCb(word_type=word_type).pack())
            )
            markup.row(
                InlineKeyboardButton(
                    text="📗 Список ключ-слов Excel",
                    callback_data=WordUploadingCb(word_type=WordType.keyword).pack()
                )
            )

        elif word_type == WordType.stopword:
            markup.row(
                InlineKeyboardButton(
                    text="➕ Стоп-слова",
                    callback_data=WordMenuAddCb(word_type=WordType.stopword).pack(),
                ),
                InlineKeyboardButton(
                    text="➖ Стоп-слова",
                    callback_data=WordMenuDeleteCb(word_type=WordType.stopword).pack(),
                ),
            )
            markup.row(
                InlineKeyboardButton(
                    text="👁️ Список стоп-слов",
                    callback_data=WordShowCb(word_type=word_type).pack())
            )
            markup.row(
                InlineKeyboardButton(
                    text="📗 Список стоп-слов Excel",
                    callback_data=WordUploadingCb(word_type=WordType.stopword).pack()
                )
            )

        markup.row(InlineKeyboardButton(text="⬅️ Вернуться назад", callback_data=back_menu_cb))

        return markup.as_markup()

    @staticmethod
    def choose_central_chat_for_excel(word_type: WordType) -> InlineKeyboardMarkup:
        from app.bot.callback_data import ChooseChatForExcelCb
        markup = InlineKeyboardBuilder()

        for chat in settings.get_central_chats():
            markup.row(
                InlineKeyboardButton(
                    text=chat.title,
                    callback_data=ChooseChatForExcelCb(word_type=word_type, chat_id=chat.chat_id).pack(),
                )
            )

        markup.row(InlineKeyboardButton(text="« Назад", callback_data=WordMenuCb(word_type=word_type).pack()))

        return markup.as_markup()

    @staticmethod
    def choose_add_words(word_type: WordType) -> InlineKeyboardMarkup:
        from app.bot.callback_data import WordExcelLoadCb, WordManualAddCb
        markup = InlineKeyboardBuilder()
        markup.row(
            InlineKeyboardButton(text='📗 Загрузить из Excel', callback_data=WordExcelLoadCb(word_type=word_type).pack())
        )
        markup.row(
            InlineKeyboardButton(text="🤚 Загрузить вручную", callback_data=WordManualAddCb(word_type=word_type).pack())
        )
        markup.row(InlineKeyboardButton(text="⬅️ Шаг назад", callback_data=WordMenuCb(word_type=word_type).pack()))

        return markup.as_markup()
