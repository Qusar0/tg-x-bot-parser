import asyncio
import app.bot.routers.admin.chats.global_state as global_state
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from app.bot.routers.admin import admin_router
from app.bot.callback_data import (
    chats_remove_cb,
    ChooseChatRemoveCb,
    NavigationChatRemoveCb,
    chats_monitoring_delete_chat_cb
)
from app.bot.routers.admin.chats.Markup import Markup
from app.bot.routers.admin.chats.State import ChatsState
from app.database.repo.Chat import ChatRepo
from app.bot.routers.admin.chats.phrases import cancel_chat_action
from .business import start_delete_chat, cancel_delete_chat


@admin_router.callback_query(ChatsState.delete_chats, F.data == cancel_chat_action)
async def cancel_deleting(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(None)

    if global_state.deleting_async_task:
        global_state.deleting_async_task.cancel()
        global_state.deleting_async_task = None

    await cancel_delete_chat(cb.message, state, False)
    await cb.answer()


@admin_router.message(ChatsState.delete_chats, F.text == cancel_chat_action)
async def cancel_deleting_msg(message: types.Message, state: FSMContext):
    await state.set_state(None)
    if global_state.deleting_async_task:
        global_state.deleting_async_task.cancel()
        global_state.deleting_async_task = None

    await cancel_delete_chat(message, state, False)


@admin_router.callback_query(F.data == chats_remove_cb)
async def delete_monitoring_chats(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(ChatsState.delete_chats)
    chats = await ChatRepo.get_monitoring_chats()
    if not chats:
        await cb.message.answer("🤷‍♂️ Чаты не найдены", reply_markup=Markup.back_menu())
        return
    chats_for_delete = []
    
    for chat in chats:
        chats_for_delete.append({'id': chat.telegram_id, 'title': chat.title, 'entity': chat.entity, 'is_choose': False})

    await state.update_data({'chats-for-delete': chats_for_delete})
    await cb.message.edit_text(
        "👇 Пожалуста, выберите нужные чаты: ",
        reply_markup=Markup.nav_show_chats_from_delete(chats_for_delete),
    )


@admin_router.callback_query(ChooseChatRemoveCb.filter())
async def choose_delete_chat_choose(cb: types.CallbackQuery, callback_data: ChooseChatRemoveCb, state: FSMContext):
    state_data = await state.get_data()
    chats = state_data.get('chats-for-delete')
    for chat in chats:
        if chat.get('id') == callback_data.chat_id:
            chat['is_choose'] = not callback_data.is_choose

    await state.update_data({'chats-for-delete': chats})

    await cb.message.edit_reply_markup(
        reply_markup=Markup.nav_show_chats_from_delete(chats, callback_data.page),
    )


@admin_router.callback_query(NavigationChatRemoveCb.filter())
async def navigate_delete_buttons(cb: types.CallbackQuery, callback_data: NavigationChatRemoveCb, state: FSMContext):
    state_data = await state.get_data()
    chats = state_data.get('chats-for-delete')
    
    direction = callback_data.direction
    page = callback_data.page

    if direction == "left":
        page -= 1
    elif direction == "right":
        page += 1

    await cb.message.edit_reply_markup(
        reply_markup=Markup.nav_show_chats_from_delete(chats, page),
    )


@admin_router.callback_query(F.data == chats_monitoring_delete_chat_cb, ChatsState.delete_chats)
async def chats_delete_scene(cb: types.CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    chats = state_data.get('chats-for-delete')
    await state.set_state(None)
    if global_state.is_deleting:
        await cb.message.edit_text("Я уже удаляю группы, пожалуйста подождите...", reply_markup=Markup.back_monitoring_chat())
        return

    chat_entities = [{'id': chat.get('id'), 'entity': chat.get('entity')} for chat in chats if chat.get('is_choose')]
    print(chat_entities)
    if not chat_entities:
        await cb.message.edit_text("<b>⚠️ Пожалуйста, выберите хотя бы 1 чат</b>", reply_markup=Markup.back_monitoring_chat())
        return

    global_state.is_deleting = True
    global_state.deleting_async_task = asyncio.ensure_future(start_delete_chat(cb.message, state, chat_entities))
    await global_state.deleting_async_task
