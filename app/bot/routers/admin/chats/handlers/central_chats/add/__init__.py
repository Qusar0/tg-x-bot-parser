import contextlib
import traceback
from loguru import logger
from aiogram import types, F
from pyrogram import types as pyrogram_types
from pyrogram.errors import UserAlreadyParticipant, ChatAdminRequired
from aiogram.fsm.context import FSMContext
from app.bot.routers.admin import admin_router
from app.bot.callback_data import chats_central_add_cb, chats_central_add_me_cb
from app.bot.routers.admin.chats.State import ChatsState
from app.bot.routers.admin.chats.Markup import Markup
from app.userbot.userbot_manager import userbot_manager
from app.bot.routers.admin.chats.helpers import extract_chat_entities
from app.database.repo.User import UserRepo
from app.settings import settings
from app.database.models.User import User
from app.bot.routers.admin.chats.handlers.open_menu import central_chats_menu


@admin_router.callback_query(F.data == chats_central_add_me_cb)
async def add_me_handler(cb: types.CallbackQuery, state: FSMContext, user: User):
    await cb.answer("Текущий чат установлен ✅", show_alert=True)
    settings.add_central_chat(user.telegram_id, user.full_name, user.exists_link_entity)
    await central_chats_menu(cb, state)


@admin_router.callback_query(F.data == chats_central_add_cb)
async def add_central_handler(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(ChatsState.add_central_chat)
    await cb.message.edit_text(
        "<b>✍️ Отправьте ссылку на чат, куда нужно пересылать сообщения:</b>",
        reply_markup=Markup.back_central_chat(is_add=True),
    )


@admin_router.message(F.text, ChatsState.add_central_chat)
async def add_central_scene(message: types.Message):
    chat_entities = extract_chat_entities(message.text)
    if not chat_entities:
        await message.answer("⚠️ Пожалуйста, укажите корректный чат", reply_markup=Markup.back_central_chat(is_add=True))
        return

    chat_entity = chat_entities[0]

    try:
        chat = await userbot_manager.get_chat(chat_entity)

        if not chat:
            await message.answer("⚠️ Чат не найден", reply_markup=Markup.back_central_chat(is_add=True))
            return

        if not isinstance(chat, pyrogram_types.ChatPreview) and chat.id in [
            chat.chat_id for chat in settings.get_central_chats()
        ]:
            await message.answer(
                "✅ <b>Такой чат уже добавлен</b>",
                reply_to_message_id=message.message_id,
                reply_markup=Markup.back_central_chat(is_add=True),
            )
            return

        if isinstance(chat, pyrogram_types.User):
            if chat.is_bot:
                await message.answer(
                    "⚠️ Нельзя указывать других ботов", reply_markup=Markup.back_central_chat(is_add=True)
                )
                return

            user = await UserRepo.get_by_telegram_id(chat.id)
            if not user:
                await message.answer(
                    "⚠️ Пользователь не найден, попросите его нажать <code>/start</code> в боте",
                    reply_markup=Markup.back_central_chat(is_add=True),
                )
                return

            settings.add_central_chat(user.telegram_id, user.full_name, user.exists_link_entity)
            await message.answer(
                "<b>✅ Пользователь добавлен и настроен</b>",
                reply_markup=Markup.back_central_chat(is_add=True),
            )
            return

        with contextlib.suppress(UserAlreadyParticipant):
            chat = await userbot_manager.join_chat(chat_entity)

        chat = await userbot_manager.get_chat(chat_entity)

        await userbot_manager.add_member(chat.id, (await message.bot.get_me()).username)
        settings.add_central_chat(chat.id, chat.title, chat_entity)

        await message.answer(
            "<b>✅ Чат добавлен и настроен</b>",
            reply_markup=Markup.back_central_chat(is_add=True),
        )

    except ChatAdminRequired:
        await message.answer(
            "⚠️ Пожалуйста, выдайте аккаунту админ права в группу, что-бы он мог добавить бота",
            reply_markup=Markup.back_central_chat(is_add=True),
        )

    except Exception as ex:
        print(traceback.print_exc())
        logger.warning(ex)
        await message.answer(f"⚠️ Что-то пошло не так {ex}", reply_markup=Markup.back_central_chat(is_add=True))
