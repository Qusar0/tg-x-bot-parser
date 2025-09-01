import asyncio
import app.bot.routers.admin.chats.global_state as global_state
from typing import List, Union
from loguru import logger
from aiogram import types
from aiogram.fsm.context import FSMContext

from pyrogram import types as pyrogram_types
from pyrogram.errors import UserAlreadyParticipant, FloodWait, UsernameNotOccupied, InviteHashExpired, InviteRequestSent

from app.bot.routers.admin.chats.Markup import Markup
from app.bot.routers.admin.chats.errors import ChatExistsError
from app.database.repo.Chat import ChatRepo
from app.bot.routers.admin.chats.error_handlers import (
    error_chat_exists_handler,
    error_flood_wait_handler,
    error_username_not_occupied_handler,
    error_chat_is_user_handler,
    error_invite_request_sent_handler,
    error_handler,
)
from app.userbot.userbot_manager import userbot_manager
from app.config import config


def get_chat_id(chat_obj) -> int | None:
    if not chat_obj:
        return ''

    chat_id = getattr(chat_obj, 'id', None)
    if chat_id:
        return chat_id

    chat_id = getattr(chat_obj, 'peer_id', None)
    if chat_id:
        return chat_id

    inner_chat = getattr(chat_obj, 'chat', None)
    if inner_chat:
        return get_chat_id(inner_chat)

    return None


def get_chat_title(chat_obj) -> str:
    if not chat_obj:
        return "Неизвестный чат"

    if title := getattr(chat_obj, 'title', ''):
        return title

    first_name = getattr(chat_obj, 'first_name', '')
    if first_name:
        last_name = getattr(chat_obj, 'last_name', '')
        return f"{first_name} {last_name}".strip()

    if username := getattr(chat_obj, 'username', ''):
        return f"@{username}"

    return "Неизвестный чат"


async def reset_store(state: FSMContext):
    global_state.is_adding = False
    global_state.added_usernames = []
    global_state.added_error_usernames = []

    await state.set_state(None)


async def send_added_chat_message_and_sleep(message: types.Message, chat_entity: str, is_last: bool):
    time_interval = config.get_sleep_time()

    if is_last:
        await message.reply(f"Чат <b>{chat_entity}</b> - добавлен! ✅", reply_markup=Markup.remove())
    else:
        await message.reply(
            f"Канал <b>{chat_entity}</b> - добавлен! ✅\n⏳ Сплю: {time_interval} сек",
            reply_markup=Markup.cancel_action(),
        )

        await asyncio.sleep(time_interval)


async def send_added_joined_chat(message: types.Message, chat_entity: str, is_last: bool):
    await message.answer(
        f"Чат <b>{chat_entity}</b> - подключен! ✅",
        reply_markup=Markup.remove() if is_last else Markup.cancel_action(),
    )


async def cancel_add_chat(message: types.Message, state: FSMContext, is_done=True):
    try:
        if not is_done:
            await message.answer("🚫 Отменяем добавление чатов", reply_markup=Markup.remove())

        title = "Добавление чатов завершено.\n\n" if is_done else "Добавление чатов отменено.\n\n"

        added_usernames_count = len(global_state.added_usernames)
        added_error_usernames_count = len(global_state.added_error_usernames)

        added_chats = "\n".join(global_state.added_usernames) if global_state.added_usernames else "Отсутствуют"
        error_chats = (
            "\n".join(global_state.added_error_usernames) if global_state.added_error_usernames else "Отсутствуют"
        )

        response_template = str(
            title + "✅ Добавленные чаты:\n" + added_chats + "\n\n🚫 Не добавленные чаты:\n" + error_chats
        )

        if added_usernames_count + added_error_usernames_count == 0:
            await message.answer(("🤷‍♂️ Новые чаты отсутствуют"), reply_markup=Markup.monitoring_chats_menu())
        elif added_usernames_count + added_error_usernames_count == 1:
            await message.answer("💬 Вернулись в меню чатов", reply_markup=Markup.monitoring_chats_menu())
        else:
            if len(response_template) <= 4096:
                await message.answer(response_template, reply_markup=Markup.monitoring_chats_menu())
            else:
                await message.answer_document(
                    types.BufferedInputFile(response_template.encode(), filename="Добавленные чаты.txt"),
                    reply_markup=Markup.monitoring_chats_menu(),
                )
    finally:
        await reset_store(state)


async def add_chat_to_db(chat_id: int, chat_title: str, chat_entity: str | None, rating: int = 0):
    await ChatRepo.add(chat_id, chat_title, chat_entity, rating)
    global_state.added_usernames.append(chat_entity)
    return True


async def join_chat(chat_entity: Union[str, int], chat: pyrogram_types.Chat | None = None, rating: int = 0) -> bool:
    try:
        candidate = await ChatRepo.get_by_entity(chat_entity)
        if candidate:
            raise ChatExistsError()

        if chat_entity.isnumeric():
            logger.debug(f"Передали числовой ID: {chat_entity}")
            await add_chat_to_db(int(chat_entity), "🟡 Приватный чат", chat_entity, rating)
            return True

        if not chat:
            chat = await userbot_manager.join_chat(chat_entity)

        chat_id = get_chat_id(chat)
        chat_title = get_chat_title(chat)

        if not chat_id:
            logger.error(f"Не удалось получить ID чата для {chat_entity}, тип объекта: {type(chat)}")
            raise ValueError(f"Не удалось получить ID чата для {chat_entity}")

        await add_chat_to_db(chat_id, chat_title, chat_entity, rating)
        return True
    except ChatExistsError as ex:
        raise ex
    except UserAlreadyParticipant:
        chat = await userbot_manager.get_chat(chat_entity)

        chat_id = get_chat_id(chat)
        chat_title = get_chat_title(chat)

        if not chat_id:
            logger.error(f"Не удалось получить ID чата для {chat_entity}, тип объекта: {type(chat)}")
            raise ValueError(f"Не удалось получить ID чата для {chat_entity}")

        await add_chat_to_db(chat_id, chat_title, chat_entity, rating)
        return True
    except Exception as ex:
        global_state.added_error_usernames.append(chat_entity)
        raise ex


async def start_subscribe(message: types.Message, state: FSMContext, chat_entities: List[str] = None, chats_data: List[dict] = None):
    if chats_data:
        chat_entities = [chat['link'] for chat in chats_data]
        chats_ratings = {chat['link']: chat['rating'] for chat in chats_data}
    else:
        chats_ratings = {}
    
    await message.answer(f"⏳ <b>Начинаю добавление, количество чатов: {len(chat_entities)}</b>")

    chats = await userbot_manager.get_dialogs(is_only_groups=True)
    exists_chats_id = [get_chat_id(chat) for chat in chats if get_chat_id(chat)]

    for chat_entity in chat_entities:
        try:
            is_last = chat_entity == chat_entities[-1]

            candidate = await userbot_manager.get_chat(chat_entity)
            candidate_id = get_chat_id(candidate)
            candidate = candidate if candidate and candidate_id in exists_chats_id else None

            chat_rating = chats_ratings.get(chat_entity, 0)
            is_added = await join_chat(chat_entity, candidate, chat_rating)
            if is_added:
                if candidate:
                    await send_added_joined_chat(message, chat_entity, is_last)
                else:
                    await send_added_chat_message_and_sleep(message, chat_entity, is_last)
        except (ChatExistsError, UserAlreadyParticipant):
            # Чат уже существует
            await error_chat_exists_handler(message, chat_entity, is_last)
        except FloodWait as ex:
            # поймали задержку
            await error_flood_wait_handler(ex, message, chat_entity, is_last)
        except (UsernameNotOccupied, InviteHashExpired):
            # username не существует
            await error_username_not_occupied_handler(message, chat_entity, is_last)
        except TypeError as ex:
            if "to any kind of inputchannel" in str(ex).lower():
                # Вместо чата отправили ссылку на пользователя
                await error_chat_is_user_handler(message, chat_entity, is_last)
            else:
                raise ex
        except InviteRequestSent:
            await error_invite_request_sent_handler(message, chat_entity, is_last)
        except ValueError as ex:
            if "no user has" in str(ex).lower():
                # Чат не существует
                await error_username_not_occupied_handler(message, chat_entity, is_last)
            else:
                raise ex
        except Exception as ex:
            print(type(ex))
            await error_handler(ex, message, chat_entity, is_last)

    return await cancel_add_chat(message, state, True)
