from pyrogram import types as pyrogram_types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from app.bot.callback_data import (
    back_menu_cb,
    chats_add_cb,
    chats_add_excel_cb,
    chats_choose_add_cb,
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
    ChatsCentralChooseCb,
    ChooseChatCb,
    ChooseChatRemoveCb,
    NavigationChatRemoveCb,
    NavigationChatCb,
    chats_uploading_cb,
    chats_change_rating_cb,
    chats_rating_winrate_cb,
    chats_re_evaluation_cb,
    ChatRatingCb,
    chats_winrate_evaluation_cb,
    chats_monitoring_delete_chat_cb,
    ChatsShowNavCb,
)
from app.database.repo.Chat import ChatRepo
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
    async def back_central_chat(is_add: bool = False) -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()

        if is_add:
            central_chats = await ChatRepo.get_central_chats()
            if not central_chats:
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
    def show_chats_nav(total: int, page: int, page_size: int) -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()

        has_prev = page > 0
        has_next = (page + 1) * page_size < total

        nav_buttons = []
        if has_prev:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="«",
                    callback_data=ChatsShowNavCb(direction="left", page=page).pack(),
                )
            )
        if has_next:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="»",
                    callback_data=ChatsShowNavCb(direction="right", page=page).pack(),
                )
            )

        if nav_buttons:
            markup.row(*nav_buttons)

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
            InlineKeyboardButton(text="➕ Чат", callback_data=chats_choose_add_cb),
            InlineKeyboardButton(text="➖ Чат", callback_data=chats_remove_cb),
        )
        markup.row(
            InlineKeyboardButton(text="💾 Выгрузить с аккаунта", callback_data=chats_load_from_account),
        )
        markup.row(
            InlineKeyboardButton(text="👁️ Список чатов", callback_data=chats_show_cb),
        )
        markup.row(
            InlineKeyboardButton(text="📗 Список чатов Excel", callback_data=chats_uploading_cb)
        )
        markup.row(
            InlineKeyboardButton(text="🏆 Изменить рейтинг/винрейт чатов", callback_data=chats_change_rating_cb)
        )
        markup.row(InlineKeyboardButton(text="⬅️ Шаг назад", callback_data=chats_cb))

        return markup.as_markup()

    @staticmethod
    def rating_winrate_chats_menu() -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()
        markup.row(
            InlineKeyboardButton(text="🏆 Указать рейтинг и винрейт", callback_data=chats_rating_winrate_cb)
        )
        markup.row(
            InlineKeyboardButton(text="🤚 Изменить рейтинг", callback_data=chats_re_evaluation_cb)
        )
        markup.row(
            InlineKeyboardButton(text="🤚 Изменить винрейт", callback_data=chats_winrate_evaluation_cb)
        )
        markup.row(
            InlineKeyboardButton(text="⬅️ Шаг назад", callback_data=chats_monitorings_cb)
        )

        return markup.as_markup()

    @staticmethod
    def choose_add_chats() -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()
        markup.row(
            InlineKeyboardButton(text='📗 Загрузить из Excel', callback_data=chats_add_excel_cb)
        )
        markup.row(
            InlineKeyboardButton(text='📂 Выбрать из аккаунта', callback_data=chats_load_from_account)
        )
        markup.row(
            InlineKeyboardButton(text="🤚 Загрузить вручную", callback_data=chats_add_cb)
        )
        markup.row(InlineKeyboardButton(text="⬅️ Шаг назад", callback_data=chats_monitorings_cb))

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
    async def remove_central_chats() -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()

        for chat in await ChatRepo.get_central_chats():
            markup.row(
                InlineKeyboardButton(
                    text=f"🗑 {chat.title} | {chat.telegram_id}",
                    callback_data=ChatsCentralDeleteCb(chat_id=chat.telegram_id).pack(),
                )
            )

        markup.row(InlineKeyboardButton(text="⬅️ Шаг назад", callback_data=chats_central_cb))

        return markup.as_markup()

    @staticmethod
    async def choose_central_chats() -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()

        for chat in await ChatRepo.get_central_chats():
            markup.row(
                InlineKeyboardButton(
                    text=f"{chat.title} | {chat.telegram_id}",
                    callback_data=ChatsCentralChooseCb(chat_id=chat.telegram_id).pack(),
                )
            )
        markup.row(InlineKeyboardButton(text="Пропустить выбор чата", callback_data=ChatsCentralChooseCb(chat_id=None).pack()))
        markup.row(InlineKeyboardButton(text="⬅️ Шаг назад", callback_data=chats_monitorings_cb))

        return markup.as_markup()

    @staticmethod
    def rating_keyboard(chat_id: int) -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()

        buttons = []
        for i in range(1, 11):
            buttons.append(
                InlineKeyboardButton(
                    text=str(i),
                    callback_data=ChatRatingCb(chat_id=chat_id, rating=i).pack()
                )
            )

        for i in range(0, len(buttons), 5):
            markup.row(*buttons[i:i + 5])

        markup.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=chats_change_rating_cb))

        return markup.as_markup()

    @staticmethod
    def chat_list_for_rating(chats: list, back_callback: str = chats_change_rating_cb, withWinrate: bool = False) -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()

        for chat in chats:
            rating_text = f"{chat.rating} ⭐" if chat.rating > 0 else "❌"
            markup.row(
                InlineKeyboardButton(
                    text=f"{rating_text} {chat.title}",
                    callback_data=f"rate_chat_winrate_{chat.telegram_id}" if withWinrate else f"rate_chat_{chat.telegram_id}"
                )
            )

        markup.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=back_callback))

        return markup.as_markup()

    @staticmethod
    def chat_list_for_winrate(chats: list, back_callback: str = chats_change_rating_cb) -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()

        for chat in chats:
            winrate_text = f"{chat.winrate}%" if chat.winrate > 0 else "❌"
            markup.row(
                InlineKeyboardButton(
                    text=f"{winrate_text} {chat.title}",
                    callback_data=f"winrate_{chat.telegram_id}"
                )
            )

        markup.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=back_callback))

        return markup.as_markup()

    @staticmethod
    def nav_show_chats_from_delete(chats: list, page: int = 0) -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()

        start = page * 10
        end = start + 10

        nav_chats = chats[start:end]
        # Добавляем кнопки в клавиатуру
        for chat in nav_chats:
            is_checked = "✅ " if chat.get('is_choose') else "❌ "

            markup.row(
                InlineKeyboardButton(
                    text=f"{is_checked} {chat.get('title')}",
                    callback_data=ChooseChatRemoveCb(chat_id=chat.get('id'), is_choose=chat.get('is_choose'), page=page).pack(),
                )
            )

        # Добавляем кнопки навигации "влево" и "вправо"
        nav_buttons = []
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton(text="«", callback_data=NavigationChatRemoveCb(direction="left", page=page).pack())
            )

        if end < len(chats):
            nav_buttons.append(
                InlineKeyboardButton(text="»", callback_data=NavigationChatRemoveCb(direction="right", page=page).pack())
            )

        markup.row(*nav_buttons)
        
        markup.row(InlineKeyboardButton(text="Отменить удаление ◀️", callback_data=cancel_chat_action))
        markup.row(InlineKeyboardButton(text="Подтвердить удаление ☑️", callback_data=chats_monitoring_delete_chat_cb))

        return markup.as_markup()