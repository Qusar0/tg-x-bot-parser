from aiogram import types, F
from aiogram.fsm.context import FSMContext
from app.bot.routers.admin import admin_router
from app.bot.routers.admin.chats.Markup import Markup
from app.database.repo.Chat import ChatRepo
from app.bot.callback_data import (
    chats_re_evaluation_cb,
    chats_without_rating_cb,
    chats_change_rating_cb,
    chats_choose_winrate,
    ChatRatingCb,
)
from app.bot.routers.admin.chats.State import ChatsState


@admin_router.callback_query(F.data == chats_change_rating_cb)
async def rating_chats_menu(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await cb.message.edit_text(
        "<b>🏆 Изменение рейтинга чатов</b>\n\n"
        "Выберите действие:",
        reply_markup=Markup.rating_chats_menu()
    )


@admin_router.callback_query(F.data == chats_without_rating_cb)
async def show_zero_rating_chats(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(None)

    chats = await ChatRepo.get_by_rating(0)

    if not chats:
        await cb.answer("✅ Все чаты уже оценены!", show_alert=True)
        return

    await cb.answer()
    await cb.message.edit_text(
        f"<b>🏆 Чаты без рейтинга ({len(chats)} шт.)</b>\n\n"
        "Выберите чат для оценки:",
        reply_markup=Markup.chat_list_for_rating(chats, chats_change_rating_cb)
    )


@admin_router.callback_query(F.data == chats_re_evaluation_cb)
async def show_all_chats_for_reevaluation(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(None)

    chats = await ChatRepo.get_by_rating_greater_than(0)

    if not chats:
        await cb.answer("❌ Чаты не найдены", show_alert=True)
        return

    await cb.answer()
    await cb.message.edit_text(
        f"<b>🤚 Переоценка чатов ({len(chats)} шт.)</b>\n\n"
        "Выберите чат для изменения рейтинга:",
        reply_markup=Markup.chat_list_for_rating(chats, chats_change_rating_cb)
    )


@admin_router.callback_query(F.data.startswith("rate_chat_"))
async def choose_rating_for_chat(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(None)

    chat_id = int(cb.data.replace("rate_chat_", ""))

    chat = await ChatRepo.get_by_telegram_id(chat_id)

    if not chat:
        await cb.answer("❌ Чат не найден", show_alert=True)
        return

    await cb.answer()
    current_rating = f"Текущий рейтинг: {chat.rating} ⭐" if chat.rating > 0 else "Текущий рейтинг: ❌ не оценён"

    await cb.message.edit_text(
        f"<b>🏆 Оценка чата</b>\n\n"
        f"<b>Чат:</b> {chat.title}\n"
        f"<b>{current_rating}</b>\n\n"
        "Выберите новый рейтинг от 1 до 10:",
        reply_markup=Markup.rating_keyboard(chat_id)
    )




@admin_router.callback_query(ChatRatingCb.filter())
async def handle_rating_selection(cb: types.CallbackQuery, callback_data: ChatRatingCb, state: FSMContext):
    await state.set_state(None)

    chat_id = callback_data.chat_id
    rating = callback_data.rating

    success = await ChatRepo.update_rating(chat_id, rating)

    if success:
        chat = await ChatRepo.get_by_telegram_id(chat_id)

        await cb.answer(f"✅ Рейтинг установлен: {rating} ⭐", show_alert=True)
        await cb.message.edit_text(
            f"<b>✅ Рейтинг успешно обновлён!</b>\n\n"
            f"<b>Чат:</b> {chat.title}\n"
            f"<b>Новый рейтинг:</b> {rating} ⭐",
            
            reply_markup=Markup.rating_chats_menu()
        )
    else:
        await cb.answer("❌ Ошибка при обновлении рейтинга", show_alert=True)
