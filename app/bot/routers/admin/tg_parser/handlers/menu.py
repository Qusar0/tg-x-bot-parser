from aiogram import types, F
from aiogram.fsm.context import FSMContext
from app.bot.routers.admin import admin_router
from app.bot.callback_data import tg_parser_cb, back_menu_cb
from app.bot.routers.admin.tg_parser.Markup import Markup


@admin_router.callback_query(F.data == tg_parser_cb)
async def tg_parser_menu(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await cb.message.edit_text(
        "<b>📱 Парсер Telegram</b>\n\n"
        "Управление словами для мониторинга Telegram чатов",
        reply_markup=Markup.open_menu(),
    )
