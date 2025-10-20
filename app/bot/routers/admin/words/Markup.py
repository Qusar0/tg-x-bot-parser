from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.enums import WordType
from app.database.repo.Chat import ChatRepo
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
    async def choose_central_chat(word_type: WordType) -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()

        for chat in await ChatRepo.get_central_chats():
            markup.row(
                InlineKeyboardButton(
                    text=chat.title,
                    callback_data=ChooseCentralChatForWordCb(word_type=word_type, chat_id=chat.telegram_id).pack(),
                )
            )

        markup.row(InlineKeyboardButton(text="« Назад", callback_data=back_menu_cb))

        return markup.as_markup()

    @staticmethod
    def delete_all_words(word_type: WordType) -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()

        # Определяем название и платформу
        is_keyword = word_type in [WordType.tg_keyword, WordType.x_keyword]
        is_stopword = word_type in [WordType.tg_stopword, WordType.x_stopword]
        is_filter_word = word_type in [WordType.tg_filter_word, WordType.x_filter_word]
        
        platform = "TG" if word_type.value.startswith("tg_") else "X"
        
        if is_keyword:
            text = f"❌ Удалить все ключ-слова {platform}"
        elif is_stopword:
            text = f"❌ Удалить все стоп-слова {platform}"
        elif is_filter_word:
            text = f"❌ Удалить все фильтр-слова {platform}"

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

        # Определяем тип слова и платформу
        is_keyword = word_type in [WordType.tg_keyword, WordType.x_keyword]
        is_stopword = word_type in [WordType.tg_stopword, WordType.x_stopword]
        is_filter_word = word_type in [WordType.tg_filter_word, WordType.x_filter_word]
        
        platform = "TG" if word_type.value.startswith("tg_") else "X"
        
        if is_keyword:
            markup.row(
                InlineKeyboardButton(
                    text=f"➕ Ключ-слова {platform}",
                    callback_data=WordMenuAddCb(word_type=word_type).pack(),
                ),
                InlineKeyboardButton(
                    text=f"➖ Ключ-слова {platform}",
                    callback_data=WordMenuDeleteCb(word_type=word_type).pack(),
                ),
            )
            markup.row(
                InlineKeyboardButton(
                    text=f"👁️ Список ключ-слов {platform}",
                    callback_data=WordShowCb(word_type=word_type).pack())
            )
            markup.row(
                InlineKeyboardButton(
                    text=f"📗 Список ключ-слов {platform} Excel",
                    callback_data=WordUploadingCb(word_type=word_type).pack()
                )
            )

        elif is_stopword:
            markup.row(
                InlineKeyboardButton(
                    text=f"➕ Стоп-слова {platform}",
                    callback_data=WordMenuAddCb(word_type=word_type).pack(),
                ),
                InlineKeyboardButton(
                    text=f"➖ Стоп-слова {platform}",
                    callback_data=WordMenuDeleteCb(word_type=word_type).pack(),
                ),
            )
            markup.row(
                InlineKeyboardButton(
                    text=f"👁️ Список стоп-слов {platform}",
                    callback_data=WordShowCb(word_type=word_type).pack())
            )
            markup.row(
                InlineKeyboardButton(
                    text=f"📗 Список стоп-слов {platform} Excel",
                    callback_data=WordUploadingCb(word_type=word_type).pack()
                )
            )
        elif is_filter_word:
            markup.row(
                InlineKeyboardButton(
                    text=f"➕ Фильтр-слова {platform}",
                    callback_data=WordMenuAddCb(word_type=word_type).pack(),
                ),
                InlineKeyboardButton(
                    text=f"➖ Фильтр-слова {platform}",
                    callback_data=WordMenuDeleteCb(word_type=word_type).pack(),
                ),
            )
            markup.row(
                InlineKeyboardButton(
                    text=f"👁️ Список фильтр-слов {platform}",
                    callback_data=WordShowCb(word_type=word_type).pack())
            )
            markup.row(
                InlineKeyboardButton(
                    text=f"📗 Список фильтр-слов {platform} Excel",
                    callback_data=WordUploadingCb(word_type=word_type).pack()
                )
            )

        markup.row(InlineKeyboardButton(text="⬅️ Вернуться назад", callback_data=back_menu_cb))

        return markup.as_markup()

    @staticmethod
    async def choose_central_chat_for_excel(word_type: WordType) -> InlineKeyboardMarkup:
        from app.bot.callback_data import ChooseChatForExcelCb
        markup = InlineKeyboardBuilder()

        for chat in await ChatRepo.get_central_chats():
            markup.row(
                InlineKeyboardButton(
                    text=chat.title,
                    callback_data=ChooseChatForExcelCb(word_type=word_type, chat_id=chat.telegram_id).pack(),
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
