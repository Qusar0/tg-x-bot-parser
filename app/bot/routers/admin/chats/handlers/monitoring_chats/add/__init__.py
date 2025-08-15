import asyncio
from loguru import logger
import app.bot.routers.admin.chats.global_state as global_state
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from app.bot.routers.admin import admin_router
from app.bot.callback_data import (
    chats_add_cb,
    chats_add_loaded_chat_cb,
    chats_load_from_account,
    ChooseChatCb,
    NavigationChatCb,
)
from app.bot.routers.admin.chats.helpers import extract_chat_entities
from app.bot.routers.admin.chats.Markup import Markup
from app.bot.routers.admin.chats.State import ChatsState
from app.database.models import Chat
from app.bot.routers.admin.chats.handlers.monitoring_chats.add.business import start_subscribe, cancel_add_chat
from app.bot.routers.admin.chats.phrases import cancel_chat_action
from app.userbot.userbot_manager import userbot_manager
from app.database.repo.Chat import ChatRepo
from app.bot.routers.admin.chats.template import get_loaded_chats_template

IS_LOADING_CHATS = False
CHATS = []


@admin_router.message(ChatsState.add, F.text == cancel_chat_action)
async def cancel_action(message: types.Message, state: FSMContext):
    await state.set_state(None)
    if global_state.adding_async_task:
        global_state.adding_async_task.cancel()
        global_state.adding_async_task = None

    await cancel_add_chat(message, state, False)


@admin_router.callback_query(F.data == chats_add_cb)
async def chats_add_handler(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(ChatsState.add)
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer(
        """
✏️ <b>Пожалуйста, отправьте ссылки на чаты, за которыми будем следить:</b>

<i>💡 Допустимые форматы:</i>
<code>@username
https://t.me/username
https://t.me/+abcd12345
https://t.me/AAAAabcd12345
</code>
""",
        reply_markup=Markup.cancel_action(),
    )


@admin_router.message(F.text, ChatsState.add)
async def chats_add_scene(message: types.Message, state: FSMContext):
    if global_state.is_adding:
        await message.answer("Я уже добавляю группы, пожалуйста подождите...", reply_markup=Markup.cancel_action())
        return

    chat_entities = extract_chat_entities(message.text)
    if not chat_entities:
        await message.answer("<b>⚠️ Пожалуйста, введите корректные чаты</b>", reply_markup=Markup.cancel_action())
        return

    global_state.is_adding = True
    global_state.adding_async_task = asyncio.ensure_future(start_subscribe(message, state, chat_entities))
    await global_state.adding_async_task


@admin_router.callback_query(F.data == chats_load_from_account)
async def load_chats_from_account(cb: types.CallbackQuery, state: FSMContext):
    global IS_LOADING_CHATS
    global CHATS

    if IS_LOADING_CHATS:
        await cb.answer("⚠️ Уже выгружаю чаты, пожалуйста подождите")
        return

    try:
        IS_LOADING_CHATS = True
        await cb.answer("⏳ Начинаю выгрузку чатов", show_alert=True)

        await state.set_state(None)
        chats = await userbot_manager.get_dialogs(is_only_groups=True)
        if not chats:
            await cb.message.answer("🤷‍♂️ Чаты на аккаунте не найдены", reply_markup=Markup.back_menu())
            return

        added_chats: list[Chat] = []

        for chat in chats:
            candidate = await ChatRepo.get_by_telegram_id(chat.id)
            if not candidate:
                # if chat.username:
                #     chat = await ChatRepo.add(
                #         chat.id,
                #         chat.title,
                #         f"@{chat.username}",
                #     )
                # else:
                #     chat = await ChatRepo.add(chat.id, chat.title)
                setattr(chat, "is_choose", False)
                added_chats.append(chat)

        if not added_chats:
            await cb.message.answer("🤷‍♂️ Новые чаты не найдены", reply_markup=Markup.back_menu())
            return

        CHATS = added_chats

        await cb.message.edit_text(
            "👇 Пожалуста, выберите нужные чаты: ",
            reply_markup=Markup.nav_show_chats_from_account(CHATS),
        )

        # raw_template, html_template = get_loaded_chats_template(added_chats)
        # if len(raw_template) < 4096:
        #     await cb.message.edit_text(
        #         html_template,
        #         reply_markup=Markup.back_monitoring_chat(),
        #     )
        # else:
        #     await cb.message.answer_document(
        #         types.BufferedInputFile(raw_template.encode(), filename="Загруженные чаты.txt"),
        #         reply_markup=Markup.delete_document(),
        #     )

    finally:
        IS_LOADING_CHATS = False


@admin_router.callback_query(ChooseChatCb.filter())
async def choose_chat_choose(cb: types.CallbackQuery, callback_data: ChooseChatCb):
    for chat in CHATS:
        if chat.id == callback_data.chat_id:
            chat.is_choose = not callback_data.is_choose

    await cb.message.edit_reply_markup(
        reply_markup=Markup.nav_show_chats_from_account(CHATS, callback_data.page),
    )


@admin_router.callback_query(NavigationChatCb.filter())
async def navigate_buttons(cb: types.CallbackQuery, callback_data: NavigationChatCb):
    direction = callback_data.direction
    page = callback_data.page

    if direction == "left":
        page -= 1
    elif direction == "right":
        page += 1

    await cb.message.edit_reply_markup(
        reply_markup=Markup.nav_show_chats_from_account(CHATS, page),
    )


@admin_router.callback_query(F.data == chats_add_loaded_chat_cb)
async def save_loaded_chats(cb: types.CallbackQuery):
    added_chats = list(filter(lambda chat: chat.is_choose, CHATS))
    chats = []
    if not added_chats:
        await cb.answer("⚠️ Пожалуйста, выберите хоть один чат", show_alert=True)
        return

    for chat in added_chats:
        try:
            if chat.username:
                chat = await ChatRepo.add(chat.id, chat.title, f"@{chat.username}")
            else:
                chat = await ChatRepo.add(chat.id, chat.title)
        except Exception as e:
            chat = await ChatRepo.get_by_telegram_id(chat.id)
        chats.append(chat)

    _, html_template = get_loaded_chats_template(chats)
    await cb.message.edit_text(
        html_template,
        reply_markup=Markup.back_monitoring_chat(),
    )
