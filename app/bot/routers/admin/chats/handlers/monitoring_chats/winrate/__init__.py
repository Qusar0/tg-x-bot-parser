from aiogram import types, F
from aiogram.fsm.context import FSMContext
from app.bot.routers.admin import admin_router
from app.bot.routers.admin.chats.Markup import Markup
from app.bot.routers.admin.tg_parser.Markup import Markup as TG_Markup
from app.bot.routers.admin.chats.helpers import extract_first_float
from app.database.repo.Chat import ChatRepo
from app.bot.callback_data import (
    chats_re_evaluation_cb,
    chats_without_rating_cb,
    chats_change_rating_cb,
    chats_choose_winrate,
    tg_parser_cb,
    ChatRatingCb,
)
from app.bot.routers.admin.chats.State import ChatsState


@admin_router.callback_query(F.data == chats_choose_winrate)
async def show_all_chats_for_reevaluation_for_winrate(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(None)

    chats = await ChatRepo.get_by_rating_greater_than(0)

    if not chats:
        await cb.answer("❌ Чаты не найдены", show_alert=True)
        return

    await cb.answer()
    await cb.message.edit_text(
        f"<b>🤚 Переоценка winrate чатов ({len(chats)} шт.)</b>\n\n"
        "Выберите чат для изменения winrate:",
        reply_markup=Markup.chat_list_for_winrate(chats, tg_parser_cb)
    )


@admin_router.callback_query(F.data.startswith("winrate_"))
async def choose_winrate_for_chat(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(ChatsState.set_winrate)

    chat_id = int(cb.data.replace("winrate_", ""))
    await state.set_data({"winrate_chat_id": chat_id})
   
    chat = await ChatRepo.get_by_telegram_id(chat_id)

    if not chat:
        await cb.answer("❌ Чат не найден", show_alert=True)
        return

    await cb.answer()
    current_winrate = f"Текущий winrate: {chat.winrate} ⭐" if chat.winrate > 0 else "Текущий winrate: ❌ не оценён"

    await cb.message.edit_text(
        f"<b>🏆 Оценка чата</b>\n\n"
        f"<b>Чат:</b> {chat.title}\n"
        f"<b>{current_winrate}</b>\n\n"
        "Выберите новый winrate:",
    )


@admin_router.message(F.text, ChatsState.set_winrate)
async def set_winrate(message: types.Message, state: FSMContext):

    data = await state.get_data()
    chat_id = data.get("winrate_chat_id")
    winrate = extract_first_float(message.text)

    await state.set_state(None)
    if not winrate:
        await message.answer("⚠️ Пожалуйста, укажите корректное значение")
        await message.answer("<b>📱 Парсер Telegram</b>\n\n"
        "Управление словами для мониторинга Telegram чатов",
            reply_markup=TG_Markup.open_menu()
        )
        return
    success = await ChatRepo.update_winrate(chat_id, winrate)

    if success:
        chat = await ChatRepo.get_by_telegram_id(chat_id)

        await message.answer(
            f"<b>✅ Winrate успешно обновлён!</b>\n\n"
            f"<b>Чат:</b> {chat.title}\n"
            f"<b>Новый winrate:</b> {winrate} ⭐",
        )
        await message.answer("<b>📱 Парсер Telegram</b>\n\n"
        "Управление словами для мониторинга Telegram чатов",
            reply_markup=TG_Markup.open_menu()
        )
    else:
        await message.answer("❌ Ошибка при обновлении winrate", show_alert=True)
