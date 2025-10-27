from aiogram import types, F
from aiogram.fsm.context import FSMContext
from app.bot.routers.admin import admin_router
from app.settings import settings
from app.bot.Markup import Markup
from app.bot.callback_data import back_menu_cb, delete_cb, x_channels_cb
from app.bot.routers.admin.x_channels.Markup import Markup as XChannelMarkup


@admin_router.message(F.text == "/start")
@admin_router.callback_query(F.data == back_menu_cb)
async def start_handler(event: types.Message | types.CallbackQuery, state: FSMContext):
    await state.set_state(None)

    if isinstance(event, types.Message):
        await event.answer(
            settings.get_template(),
            reply_markup=Markup.open_menu(),
        )
    else:
        await event.message.edit_text(
            settings.get_template(),
            reply_markup=Markup.open_menu(),
        )


@admin_router.callback_query(F.data == delete_cb)
async def delete_handler(cb: types.CallbackQuery):
    await cb.message.delete()


@admin_router.callback_query(F.data == x_channels_cb)
async def x_channels_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🔗 <b>Управление X каналами</b>\n\n"
        "Выберите действие:",
        reply_markup=XChannelMarkup.x_channels_menu()
    )
    await callback.answer()
