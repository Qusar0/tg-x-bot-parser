from aiogram import types, F
from aiogram.fsm.context import FSMContext
from app.bot.routers.admin import admin_router
from app.bot.callback_data import chats_central_remove_cb, ChatsCentralDeleteCb
from app.bot.routers.admin.chats.Markup import Markup
from app.settings import settings


@admin_router.callback_query(F.data == chats_central_remove_cb)
async def open_menu(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await cb.message.edit_text(
        "🗑 Пожалуйста, нажмите на чат, который нужно удалить",
        reply_markup=Markup.remove_central_chats(),
    )


@admin_router.callback_query(ChatsCentralDeleteCb.filter())
async def delete_scene(cb: types.CallbackQuery, callback_data: ChatsCentralDeleteCb, state: FSMContext):
    if len(settings.get_central_chats()) <= 1:
        await cb.answer("⚠️ Нельзя удалить единственный чат", show_alert=True)
        return

    settings.remove_central_chat(callback_data.chat_id)
    await cb.answer("✔️ Чат удален")
    await cb.message.edit_reply_markup(
        reply_markup=Markup.remove_central_chats(),
    )
