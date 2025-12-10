from aiogram import types, F, Router
from aiogram.fsm.context import FSMContext
from app.bot.routers.admin import admin_router

router = Router()
from app.bot.routers.admin.x_channels.Markup import Markup
from app.bot.routers.admin.x_channels.State import XChannelStates
from app.bot.routers.admin.chats.State import ChatsState
from app.database.repo.XChannel import XChannelRepo
from app.bot.callback_data import (
    x_channels_rating_cb,
    x_channels_without_rating_cb,
    x_channels_re_evaluation_cb,
    XChannelRatingCb,
)


@router.callback_query(F.data == x_channels_rating_cb)
async def rating_x_channels_menu(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await cb.message.edit_text(
        "<b>🏆 Изменение рейтинга X каналов</b>\n\n"
        "Выберите действие:",
        reply_markup=Markup.rating_x_channels_menu()
    )


@router.callback_query(F.data == x_channels_without_rating_cb)
async def show_zero_rating_x_channels(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(None)

    channels = await XChannelRepo.get_by_rating(0)

    if not channels:
        await cb.answer("✅ Все каналы уже оценены!", show_alert=True)
        return

    await cb.answer()
    await cb.message.edit_text(
        f"<b>🏆 X каналы без рейтинга ({len(channels)} шт.)</b>\n\n"
        "Выберите канал для оценки:",
        reply_markup=await Markup.channel_list_for_rating(channels, x_channels_rating_cb)
    )


@router.callback_query(F.data == x_channels_re_evaluation_cb)
async def show_all_x_channels_for_reevaluation(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(None)

    channels = await XChannelRepo.get_by_rating_greater_than(0)

    if not channels:
        await cb.answer("❌ Каналы не найдены", show_alert=True)
        return

    await cb.answer()
    await cb.message.edit_text(
        f"<b>🔄 Переоценка X каналов ({len(channels)} шт.)</b>\n\n"
        "Выберите канал для изменения рейтинга:",
        reply_markup=await Markup.channel_list_for_rating(channels, x_channels_rating_cb)
    )


@router.callback_query(F.data.startswith("rate_x_channel_"))
async def choose_rating_for_x_channel(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(None)

    channel_id = int(cb.data.replace("rate_x_channel_", ""))

    channel = await XChannelRepo.get_by_id(channel_id)

    if not channel:
        await cb.answer("❌ Канал не найден", show_alert=True)
        return

    await cb.answer()
    current_rating = f"Текущий рейтинг: {channel.rating} ⭐" if channel.rating > 0 else "Текущий рейтинг: ❌ не оценён"

    await cb.message.edit_text(
        f"<b>🏆 Оценка X канала</b>\n\n"
        f"<b>Канал:</b> {channel.title}\n"
        f"<b>URL:</b> {channel.url}\n"
        f"<b>{current_rating}</b>\n\n"
        "Выберите новый рейтинг от 1 до 10:",
        reply_markup=Markup.rating_keyboard(channel_id)
    )


@router.callback_query(XChannelRatingCb.filter(), XChannelStates.add_raiting_winrate)
async def handle_x_channel_rating_selection(cb: types.CallbackQuery, callback_data: XChannelRatingCb, state: FSMContext):
    await state.set_state(ChatsState.set_x_winrate)

    channel_id = callback_data.channel_id
    rating = callback_data.rating

    success = await XChannelRepo.update_rating(channel_id, rating)

    if success:
        channel = await XChannelRepo.get_by_id(channel_id)

        await cb.answer(f"✅ Рейтинг установлен: {rating} ⭐", show_alert=True)
        await cb.message.edit_text(
            f"<b>✅ Рейтинг успешно обновлён!</b>\n\n"
            f"<b>Канал:</b> {channel.title}\n"
            f"<b>URL:</b> {channel.url}\n"
            f"<b>Новый рейтинг:</b> {rating} ⭐"
            "Винрейт",
            reply_markup=Markup.cancel_action()
        )
    else:
        await cb.answer("❌ Ошибка при обновлении рейтинга", show_alert=True)


@router.callback_query(XChannelRatingCb.filter())
async def handle_x_channel_rating_selection(cb: types.CallbackQuery, callback_data: XChannelRatingCb, state: FSMContext):
    await state.set_state(None)

    channel_id = callback_data.channel_id
    rating = callback_data.rating

    success = await XChannelRepo.update_rating(channel_id, rating)

    if success:
        channel = await XChannelRepo.get_by_id(channel_id)

        await cb.answer(f"✅ Рейтинг установлен: {rating} ⭐", show_alert=True)
        await cb.message.edit_text(
            f"<b>✅ Рейтинг успешно обновлён!</b>\n\n"
            f"<b>Канал:</b> {channel.title}\n"
            f"<b>URL:</b> {channel.url}\n"
            f"<b>Новый рейтинг:</b> {rating} ⭐",
            reply_markup=Markup.rating_x_channels_menu()
        )
    else:
        await cb.answer("❌ Ошибка при обновлении рейтинга", show_alert=True)
