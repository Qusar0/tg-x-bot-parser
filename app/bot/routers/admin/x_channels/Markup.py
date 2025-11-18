from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from app.bot.callback_data import (
    back_menu_cb,
    x_channels_cb,
    x_channels_add_cb,
    x_channels_choose_add_cb,
    x_channels_add_excel_cb,
    x_channels_remove_cb,
    x_channels_show_cb,
    x_channels_uploading_cb,
    x_channels_rating_cb,
    x_channels_without_rating_cb,
    x_channels_re_evaluation_cb,
    XChannelDeleteCb,
    XChannelRatingCb,
)
from app.database.repo.XChannel import XChannelRepo
from app.database.repo.Chat import ChatRepo
from app.bot.callback_data import ChatsCentralChooseCb
from .phrases import cancel_chat_action


class Markup:
    @staticmethod
    def x_channels_menu() -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()
        markup.row(
            InlineKeyboardButton(text="➕ Канал", callback_data=x_channels_choose_add_cb),
            InlineKeyboardButton(text="➖ Канал", callback_data=x_channels_remove_cb),
        )
        markup.row(
            InlineKeyboardButton(text="👁️ Список каналов", callback_data=x_channels_show_cb),
        )
        markup.row(
            InlineKeyboardButton(text="📗 Список каналов Excel", callback_data=x_channels_uploading_cb)
        )
        markup.row(
            InlineKeyboardButton(text="🏆 Рейтинг каналов", callback_data=x_channels_rating_cb)
        )
        markup.row(InlineKeyboardButton(text="⬅️ Шаг назад", callback_data=back_menu_cb))

        return markup.as_markup()

    @staticmethod
    def choose_add_x_channels() -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()
        markup.row(
            InlineKeyboardButton(text='📗 Загрузить из Excel', callback_data=x_channels_add_excel_cb)
        )
        markup.row(
            InlineKeyboardButton(text="🤚 Загрузить вручную", callback_data=x_channels_add_cb)
        )
        markup.row(InlineKeyboardButton(text="⬅️ Шаг назад", callback_data=x_channels_cb))

        return markup.as_markup()

    @staticmethod
    async def remove_x_channels() -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()

        channels = await XChannelRepo.get_all()
        for channel in channels:
            markup.row(
                InlineKeyboardButton(
                    text=f"🗑 {channel.title}",
                    callback_data=XChannelDeleteCb(channel_id=channel.id).pack(),
                )
            )

        markup.row(InlineKeyboardButton(text="⬅️ Шаг назад", callback_data=x_channels_cb))

        return markup.as_markup()

    @staticmethod
    def cancel_action() -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()
        markup.row(InlineKeyboardButton(text="⬅️ Шаг назад", callback_data=x_channels_cb))
        return markup.as_markup()

    @staticmethod
    def remove() -> ReplyKeyboardRemove:
        return ReplyKeyboardRemove()

    @staticmethod
    def back_menu() -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()
        markup.row(InlineKeyboardButton(text="⬅️ Вернуться назад", callback_data=x_channels_cb))
        return markup.as_markup()

    @staticmethod
    def rating_x_channels_menu() -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()
        markup.row(
            InlineKeyboardButton(text="❌ Без рейтинга", callback_data=x_channels_without_rating_cb),
            InlineKeyboardButton(text="🔄 Переоценка", callback_data=x_channels_re_evaluation_cb),
        )
        markup.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=x_channels_cb))
        return markup.as_markup()

    @staticmethod
    def rating_keyboard(channel_id: int) -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()

        buttons = []
        for i in range(1, 11):
            buttons.append(
                InlineKeyboardButton(
                    text=str(i),
                    callback_data=XChannelRatingCb(channel_id=channel_id, rating=i).pack()
                )
            )

        for i in range(0, len(buttons), 5):
            markup.row(*buttons[i:i + 5])

        markup.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=x_channels_rating_cb))

        return markup.as_markup()

    @staticmethod
    async def channel_list_for_rating(channels: list, back_callback: str = x_channels_rating_cb) -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()

        for channel in channels:
            rating_text = f"{channel.rating} ⭐" if channel.rating > 0 else "❌"
            markup.row(
                InlineKeyboardButton(
                    text=f"{rating_text} {channel.title}",
                    callback_data=f"rate_x_channel_{channel.id}"
                )
            )

        markup.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=back_callback))

        return markup.as_markup()
    
    @staticmethod
    async def channel_list_for_winrate(channels: list, back_callback: str = x_channels_rating_cb) -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()

        for channel in channels:
            winrate_text = f"{channel.winrate} ⭐" if channel.winrate > 0 else "❌"
            markup.row(
                InlineKeyboardButton(
                    text=f"{winrate_text} {channel.title}",
                    callback_data=f"winratex_channel_{channel.id}"
                )
            )

        markup.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=back_callback))

        return markup.as_markup()


    @staticmethod
    async def choose_central_chats() -> InlineKeyboardMarkup:
        markup = InlineKeyboardBuilder()

        for chat in await ChatRepo.get_central_chats():
            markup.row(
                InlineKeyboardButton(
                    text=f"🗑 {chat.title} | {chat.telegram_id}",
                    callback_data=ChatsCentralChooseCb(chat_id=chat.telegram_id).pack(),
                )
            )

        markup.row(InlineKeyboardButton(text="⬅️ Шаг назад", callback_data=x_channels_cb))

        return markup.as_markup()

