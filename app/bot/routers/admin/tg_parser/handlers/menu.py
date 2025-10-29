from aiogram import types, F
from aiogram.fsm.context import FSMContext
from app.bot.routers.admin import admin_router
from app.bot.callback_data import tg_parser_cb, back_menu_cb, ChangeSettingsCb
from app.bot.routers.admin.tg_parser.Markup import Markup
from app.settings import settings


@admin_router.callback_query(F.data == tg_parser_cb)
async def tg_parser_menu(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await cb.message.edit_text(
        "<b>📱 Парсер Telegram</b>\n\n"
        "Управление словами для мониторинга Telegram чатов",
        reply_markup= Markup.open_menu(),
    )


@admin_router.callback_query(ChangeSettingsCb.filter())
async def toggle_source_setting(cb: types.CallbackQuery, callback_data: ChangeSettingsCb, state: FSMContext):
    """Toggle whether to include source in messages sent by the bot for Telegram platform."""
    if callback_data.field != "source_tg":
        await cb.answer()
        return

    new_value = bool(callback_data.value)
    try:
        settings.set_source_tg(new_value)
    except Exception:
        pass

    try:
        await cb.message.edit_reply_markup(reply_markup=Markup.open_menu())
        await cb.answer(text=("Указание источника включено" if new_value else "Указание источника отключено"))
    except Exception as e:
        await cb.answer(text="Ошибка обновления панели")
