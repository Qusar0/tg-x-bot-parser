import asyncio
import app.bot.routers.admin.chats.global_state as global_state
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from app.bot.routers.admin import admin_router
from app.bot.callback_data import chats_remove_cb
from app.bot.routers.admin.chats.helpers import extract_chat_entities
from app.bot.routers.admin.chats.Markup import Markup
from app.bot.routers.admin.chats.State import ChatsState
from app.bot.routers.admin.chats.phrases import cancel_chat_action
from .business import start_delete_chat, cancel_delete_chat


@admin_router.message(ChatsState.delete, F.text == cancel_chat_action)
async def cancel_deleting(message: types.Message, state: FSMContext):
    await state.set_state(None)
    if global_state.deleting_async_task:
        global_state.deleting_async_task.cancel()
        global_state.deleting_async_task = None

    await cancel_delete_chat(message, state, False)


@admin_router.callback_query(F.data == chats_remove_cb)
async def chats_delete_handler(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(ChatsState.delete)
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer(
        """
🗑 <b>Пожалуйста, отправьте ссылки на чаты, которые нужно удалить:</b>

<i>💡 Допустимые форматы:</i>
<code>@username
https://t.me/username
https://t.me/+abcd12345
https://t.me/AAAAabcd12345
</code>
""",
        reply_markup=Markup.cancel_action(),
    )


@admin_router.message(F.text, ChatsState.delete)
async def chats_delete_scene(message: types.Message, state: FSMContext):
    if global_state.is_deleting:
        await message.answer("Я уже удаляю группы, пожалуйста подождите...", reply_markup=Markup.cancel_action())
        return

    chat_entities = extract_chat_entities(message.text)
    if not chat_entities:
        await message.answer("<b>⚠️ Пожалуйста, введите корректные чаты</b>", reply_markup=Markup.cancel_action())
        return

    global_state.is_deleting = True
    global_state.deleting_async_task = asyncio.ensure_future(start_delete_chat(message, state, chat_entities))
    await global_state.deleting_async_task
