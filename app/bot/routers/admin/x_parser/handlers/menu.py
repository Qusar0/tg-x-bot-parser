from aiogram import types, F
from aiogram.fsm.context import FSMContext
from app.bot.routers.admin import admin_router
from app.bot.callback_data import x_parser_cb, back_menu_cb, ChangeSettingsCb
from app.bot.routers.admin.x_parser.Markup import Markup
from app.settings import settings


@admin_router.callback_query(F.data == x_parser_cb)
async def x_parser_menu(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await cb.message.edit_text(
        "<b>🐦 Парсер X (Twitter)</b>\n\n"
        "Управление словами для парсинга X",
        reply_markup=Markup.open_menu(),
    )


@admin_router.callback_query(ChangeSettingsCb.filter())
async def toggle_source_x(cb: types.CallbackQuery, callback_data: ChangeSettingsCb, state: FSMContext):
    if callback_data.field != "source_x":
        await cb.answer()
        return

    new_value = bool(callback_data.value)
    try:
        settings.set_source_x(new_value)
    except Exception:
        pass

    try:
        await cb.message.edit_reply_markup(reply_markup=Markup.open_menu())
        await cb.answer(text=("Указание источника включено" if new_value else "Указание источника отключено"))
    except Exception as e:
        await cb.answer(text="Ошибка обновления панели")
