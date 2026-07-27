import asyncio
import app.bot.routers.admin.chats.global_state as global_state
from loguru import logger
from typing import List, Union
from aiogram import types
from aiogram.fsm.context import FSMContext
from pyrogram.errors import (
    FloodWait,
    UserNotParticipant,
    UsernameNotOccupied,
    UsernameInvalid,
    ChannelInvalid,
    ChannelPrivate
)

from app.bot.routers.admin.chats.Markup import Markup
from app.userbot.userbot_manager import userbot_manager

from app.database.repo.Chat import ChatRepo

from app.bot.routers.admin.chats.error_handlers import (
    error_flood_wait_handler,
    error_handler_delete_chat,
    chat_not_exists_handler,
    error_username_not_occupied_handler
)
from app.bot.routers.admin.chats.errors import ChatNotExistError
from app.config import config


async def reset_store(state: FSMContext) -> None:
    global_state.is_deleting = False
    global_state.deleted_usernames = []
    global_state.deleted_error_usernames = []

    await state.set_state(None)


async def send_deleted_chat_message_and_sleep(message: types.Message, chat_entity: str, is_last: bool) -> None:
    time_interval = config.get_sleep_time()

    if is_last:
        await message.answer(
            f"Чат <b>{chat_entity}</b> - удален! ✅",
            reply_markup=Markup.remove(),
        )
    else:
        await message.answer(
            f"Канал <b>{chat_entity}</b> - удален! ✅\n⏳ Сплю: {time_interval} сек",
            reply_markup=Markup.back_monitoring_chat(),
        )

        await asyncio.sleep(time_interval)


async def cancel_delete_chat(message: types.Message, state: FSMContext, is_done=True) -> None:
    try:
        if not is_done:
            await message.edit_text("🚫 Отменяем удаление чатов")

        title = "Удаление чатов завершено.\n\n" if is_done else "Удаление чатов отменено.\n\n"

        deleted_usernames_count = len(global_state.deleted_usernames)
        deleted_error_usernames_count = len(global_state.deleted_error_usernames)

        deleted_chats = "\n".join(str(x) for x in global_state.deleted_usernames) if global_state.deleted_usernames else "Отсутствуют"
        error_chats = (
            "\n".join(str(x) for x in global_state.deleted_error_usernames) if global_state.deleted_error_usernames else "Отсутствуют"
        )

        response_template = str(
            title + "✅ Удаленные чаты:\n" + deleted_chats + "\n\n🚫 Не удаленные чаты:\n" + error_chats
        )

        if deleted_usernames_count + deleted_error_usernames_count == 0:
            await message.answer("🤷‍♂️ Удаленные чаты отсутствуют", reply_markup=Markup.open_menu())
        elif deleted_usernames_count + deleted_error_usernames_count == 1:
            await message.answer("Вернулись в меню чатов", reply_markup=Markup.open_menu())
        else:
            if len(response_template) <= 4096:
                await message.answer(response_template, reply_markup=Markup.open_menu())
            else:
                await message.answer_document(
                    types.BufferedInputFile(response_template.encode(), filename="Удаленные чаты.txt"),
                    reply_markup=Markup.open_menu(),
                )
    finally:
        await reset_store(state)


async def leave_chat(chat_entity: Union[str, int]) -> bool:
    try:
        candidate = await ChatRepo.get_by_telegram_id(chat_entity)
        if not candidate:
            raise ChatNotExistError()

        await userbot_manager.leave_chat(chat_entity)
        await ChatRepo.delete(candidate.telegram_id)

        global_state.deleted_usernames.append(str(chat_entity))
        return True
    except ChannelPrivate:
        logger.warning(f"Приватный канал: {chat_entity}")
        await ChatRepo.delete(candidate.telegram_id)
        global_state.deleted_usernames.append(chat_entity)
        return True
    except ChannelInvalid:
        logger.warning(f"Неверный канал с ID: {chat_entity}")
        await ChatRepo.delete(candidate.telegram_id)
        global_state.deleted_usernames.append(chat_entity)
        return True
    except UserNotParticipant:
        logger.warning(f"Аккаунта нету в группе: {chat_entity}")
        await ChatRepo.delete(candidate.telegram_id)
        global_state.deleted_usernames.append(chat_entity)
        return True
    except UsernameNotOccupied:
        logger.warning(f"Username не занят: {chat_entity}")
        await ChatRepo.delete(candidate.telegram_id)
        global_state.deleted_usernames.append(chat_entity)
        return True
    except UsernameInvalid:
        logger.warning(f"Username невалидный: {chat_entity}")
        await ChatRepo.delete(candidate.telegram_id)
        global_state.deleted_usernames.append(chat_entity)
        return True
    except Exception as ex:
        global_state.deleted_error_usernames.append(chat_entity)
        raise ex


async def start_delete_chat(message: types.Message, state: FSMContext, chat_entities: List[str]) -> None:
    await message.edit_text(f"<b>Начинаю удаление, количество чатов: {len(chat_entities)}</b>")

    for chat_dict in chat_entities:
        try:
            chat_entity = chat_dict.get('id') if chat_dict.get('entity') is None else chat_dict.get('entity')
            chat_id = chat_dict.get('id')
            is_last = chat_entity == chat_entities[-1]
            is_deleted = await leave_chat(chat_id)
            if is_deleted:
                await send_deleted_chat_message_and_sleep(message, chat_entity, is_last)
        except ChatNotExistError:
            await chat_not_exists_handler(message, chat_entity, is_last)
        except FloodWait as ex:
            await error_flood_wait_handler(ex, message, chat_entity, is_last)
        except (UsernameNotOccupied, UsernameInvalid):
            await error_username_not_occupied_handler(message, chat_entity, is_last)
        except Exception as ex:
            await error_handler_delete_chat(ex, message, chat_entity, is_last)

    return await cancel_delete_chat(message, state, True)
