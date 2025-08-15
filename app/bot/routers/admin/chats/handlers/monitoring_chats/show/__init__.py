from aiogram import types, F
from aiogram.fsm.context import FSMContext
from app.bot.routers.admin import admin_router
from app.bot.callback_data import chats_show_cb
from app.database.repo.Chat import ChatRepo
from app.bot.routers.admin.chats.Markup import Markup
from app.bot.routers.admin.chats.template import get_chats_template


@admin_router.callback_query(F.data == chats_show_cb)
async def chats_show(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(None)

    chats = await ChatRepo.get_all()

    if not chats:
        await cb.answer("🤷‍♂️ Чаты еще не добавлены", show_alert=True)
        return

    await cb.answer()

    raw_template, html_template = get_chats_template(chats)

    if len(raw_template) <= 4096:
        await cb.message.edit_text(html_template, reply_markup=Markup.back_monitoring_chat())
    else:
        await cb.message.answer_document(
            types.BufferedInputFile(raw_template.encode(), filename="Список чатов.txt"),
            reply_markup=Markup.delete_document(),
        )
