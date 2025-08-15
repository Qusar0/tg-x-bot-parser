from aiogram import types, F
from aiogram.fsm.context import FSMContext
from app.bot.routers.admin import admin_router
from app.bot.callback_data import chats_cb, chats_monitorings_cb, chats_central_cb
from app.bot.routers.admin.chats.Markup import Markup
from app.settings import settings
from app.database.repo.User import UserRepo


@admin_router.callback_query(F.data == chats_cb)
async def open_menu(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await cb.message.edit_text(
        "<b>💬 Перешли в меню чатов</b>",
        reply_markup=Markup.open_menu(),
    )


@admin_router.callback_query(F.data == chats_monitorings_cb)
async def monitoring_chats_menu(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await cb.message.edit_text(
        "<b>💬 Перешли в меню мониторинг чатов</b>",
        reply_markup=Markup.monitoring_chats_menu(),
    )


@admin_router.callback_query(F.data == chats_central_cb)
async def central_chats_menu(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(None)
    central_chats = settings.get_central_chats()

    template = "<b>🤷‍♀️ Чаты для переотправки еще не добавлены</b>"

    if central_chats:
        template = "<b>💬 Текущие чаты, куда переотправляются все сообщения:</b>"
        for num, chat in enumerate(central_chats, start=1):
            user = await UserRepo.get_by_telegram_id(chat.chat_id)
            if user:
                template += f"\n<i>{num}.</i> <a href='{user.exists_link_entity}'>{user.full_name}</a> | <code>{chat.chat_id}</code>"  # noqa
            else:
                template += f"\n<i>{num}.</i> <a href='{chat.entity}'>{chat.title}</a> | <code>{chat.chat_id}</code>"

    await cb.message.edit_text(
        template,
        reply_markup=Markup.central_chats_menu(),
    )
