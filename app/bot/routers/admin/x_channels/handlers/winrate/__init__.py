from aiogram import types, F, Router
from aiogram.fsm.context import FSMContext
from app.bot.routers.admin import admin_router
from app.bot.routers.admin.x_channels.Markup import Markup
from app.bot.routers.admin.x_parser.Markup import Markup as X_Markup
from app.bot.routers.admin.chats.helpers import extract_first_float
from app.database.repo.XChannel import XChannelRepo
from app.bot.callback_data import (
    x_channels_choose_winrate,
    x_channels_winrate_evaluation_cb,
    x_channels_without_winrate_cb,
    x_parser_cb,
)
from app.bot.routers.admin.chats.State import ChatsState

router = Router()

@router.callback_query(F.data == x_channels_choose_winrate)
async def rating_x_channels_menu(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await cb.message.edit_text(
        "<b>🏆 Изменение winrate X каналов</b>\n\n"
        "Выберите действие:",
        reply_markup=Markup.winrate_x_channels_menu()
    )


@router.callback_query(F.data == x_channels_without_winrate_cb)
async def show_zero_rating_x_channels(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(None)

    channels = await XChannelRepo.get_by_winrate(0)

    if not channels:
        await cb.answer("✅ Все каналы уже оценены!", show_alert=True)
        return

    await cb.answer()
    await cb.message.edit_text(
        f"<b>🏆 X каналы без winrate ({len(channels)} шт.)</b>\n\n"
        "Выберите канал для оценки:",
        reply_markup=await Markup.channel_list_for_winrate(channels, x_channels_choose_winrate)
    )

@admin_router.callback_query(F.data == x_channels_winrate_evaluation_cb)
async def show_all_chats_for_reevaluation_for_winrate(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(None)

    chats = await XChannelRepo.get_by_winrate_greater_than(0)

    if not chats:
        await cb.answer("❌ Каналы не найдены", show_alert=True)
        return

    await cb.answer()
    await cb.message.edit_text(
        f"<b>🤚 Переоценка winrate каналов ({len(chats)} шт.)</b>\n\n"
        "Выберите чат для изменения winrate:",
        reply_markup=await Markup.channel_list_for_winrate(chats, x_channels_choose_winrate)
    )


@admin_router.callback_query(F.data.startswith("winratex_channel_"))
async def choose_winrate_for_chat(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(ChatsState.set_x_winrate)

    channel_id = int(cb.data.replace("winratex_channel_", ""))
    await state.set_data({"winrate_x_channel_id": channel_id})
   
    channel = await XChannelRepo.get_by_id(channel_id)

    if not channel:
        await cb.answer("❌ Чат не найден", show_alert=True)
        return

    await cb.answer()
    current_winrate = f"Текущий winrate: {channel.winrate}%" if channel.winrate > 0 else "Текущий winrate: ❌ не оценён"

    await cb.message.edit_text(
        f"<b>🏆 Оценка чата</b>\n\n"
        f"<b>Чат:</b> {channel.title}\n"
        f"<b>{current_winrate}</b>\n\n"
        "Выберите новый winrate:",
    )


@admin_router.message(F.text, ChatsState.set_x_winrate)
async def set_winrate(message: types.Message, state: FSMContext):

    data = await state.get_data()
    channel_id = data.get("winrate_x_channel_id")
    winrate = extract_first_float(message.text)
    print(winrate)

    await state.set_state(None)
    if not winrate:
        await message.answer("⚠️ Пожалуйста, укажите корректное значение")
        await message.answer("<b>🐦 Парсер X (Twitter)</b>\n\n"
        "Управление словами для парсинга X",
            reply_markup=X_Markup.open_menu()
        )
        return
    success = await XChannelRepo.update_winrate(channel_id, winrate)

    if success:
        chat = await XChannelRepo.get_by_id(channel_id)

        await message.answer(
            f"<b>✅ Winrate успешно обновлён!</b>\n\n"
            f"<b>Чат:</b> {chat.title}\n"
            f"<b>Новый winrate:</b> {winrate}%",
        )
        await message.answer("<b>🐦 Парсер X (Twitter)</b>\n\n"
        "Управление словами для парсинга X",
            reply_markup=X_Markup.open_menu()
        )
    else:
        await message.answer("❌ Ошибка при обновлении winrate", show_alert=True)
