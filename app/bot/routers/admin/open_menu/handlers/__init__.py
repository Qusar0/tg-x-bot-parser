from aiogram import types, F
from aiogram.fsm.context import FSMContext
from app.bot.routers.admin import admin_router
from app.settings import settings
from app.bot.Markup import Markup
from app.bot.callback_data import back_menu_cb, delete_cb


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
        if event.message.document or event.message.photo or event.message.video or event.message.audio or event.message.voice or event.message.sticker:
            await event.message.answer(
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
