from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.bot.callback_data import back_menu_cb, WordMenuCb, ChangeSettingsCb, chats_choose_winrate
from app.enums import WordType
from app.settings import settings


class Markup:
    @staticmethod
    def open_menu() -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()

        try:
            enabled = bool(settings.get_source_tg())
        except Exception:
            enabled = True

        markup.row(
            InlineKeyboardButton(
                text="🔑 Ключ-слова TG", 
                callback_data=WordMenuCb(word_type=WordType.tg_keyword).pack()
            ),
            InlineKeyboardButton(
                text="🛑 Стоп-слова TG", 
                callback_data=WordMenuCb(word_type=WordType.tg_stopword).pack()
            ),
        )
        markup.row(
            InlineKeyboardButton(
                text="🔍 Фильтр-слова TG", 
                callback_data=WordMenuCb(word_type=WordType.tg_filter_word).pack()
            ),
        )
        # TODO: Добавить зеленый кружочек и его смену на красный, то есть сделать возможным переключение указания источника"
        # TODO: Написать каллбек функцию, чтоб она скажем отключала указания источников в сообщениях 
        # TODO: (надо сначала найти в какой момент отправляется сообщение с указанием источника, какая кнопка нажимается), 
        # TODO: пересылаемых в чаты, и подключить ее
        # TODO: в два места - тут и в x_parser
        # Кнопка переключения указания источника: зеленый кружок = включено, красный = выключено
        circle = "🟢" if enabled else "🔴"
        toggle_cb = ChangeSettingsCb(field="source_tg", value=not enabled).pack()

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

