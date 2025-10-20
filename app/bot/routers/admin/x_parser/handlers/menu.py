from aiogram import types, F
from aiogram.fsm.context import FSMContext
from app.bot.routers.admin import admin_router
from app.bot.callback_data import x_parser_cb, back_menu_cb
from app.bot.routers.admin.x_parser.Markup import Markup


@admin_router.callback_query(F.data == x_parser_cb)
async def x_parser_menu(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await cb.message.edit_text(
        "<b>🐦 Парсер X (Twitter)</b>\n\n"
        "Управление словами для парсинга X",
        reply_markup=Markup.open_menu(),
    )
