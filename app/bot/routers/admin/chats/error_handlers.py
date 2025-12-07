import asyncio
from loguru import logger
from aiogram import types
from pyrogram.errors import FloodWait
from app.bot.routers.admin.chats.Markup import Markup
from app.config import config


def get_markup(is_last: bool):
    return Markup.remove() if is_last else Markup.cancel_action()


async def error_chat_exists_handler(message: types.Message, chat_entity: str, is_last: bool):
    await message.answer(
        f"Чат <b>{chat_entity}</b> уже добавлен! ✅",
        reply_markup=get_markup(is_last),
    )
    await asyncio.sleep(1)


async def error_flood_wait_handler(ex: FloodWait, message: types.Message, chat_entity: str, is_last: bool):
    time_sleep = ex.value + config.get_sleep_time()

    await message.answer(
        f"⚠️ Я словил FloodWait на {time_sleep} сек: {chat_entity}",
        reply_markup=get_markup(is_last),
    )

    if not is_last:
        await asyncio.sleep(time_sleep)


async def error_username_not_occupied_handler(message: types.Message, chat_entity: str, is_last: bool):
    time_sleep = config.get_sleep_time()

    if is_last:
        await message.answer(
            f"⚠️ Чат не существует: {chat_entity}",
            reply_markup=get_markup(is_last),
        )
    else:
        await message.answer(
            f"⚠️ Чат не существует: {chat_entity}\n⏳ Сплю: {time_sleep} сек",
            reply_markup=get_markup(is_last),
        )
        await asyncio.sleep(time_sleep)


async def error_invite_request_sent_handler(message: types.Message, chat_entity: str, is_last: bool):
    await message.answer(
        f"<b>❗️Заявка на вступление отправлена</b>, пожалуйста, после одобрения <u>отправьте ссылку еще раз:</u> {chat_entity}",  # noqa: E501
        reply_markup=get_markup(is_last),
    )


async def chat_not_exists_handler(message: types.Message, chat_entity: str, is_last: bool):
    await message.answer(
        f"⚠️ Чат не существует в базе данных: {chat_entity}",
        reply_markup=get_markup(is_last),
    )
    await asyncio.sleep(1)


async def error_chat_is_user_handler(message: types.Message, chat_entity: str, is_last: bool):
    await message.answer(
        f"⚠️ Внимание, это пользователь, не чат: {chat_entity}",
        reply_markup=get_markup(is_last),
    )
    await asyncio.sleep(1)


async def error_handler(ex: Exception, message: types.Message, chat_entity: str, is_last: bool):
    logger.error(f"Что-то пошло не так при добавлении чата {ex}")

    await message.reply(
        f"Чат: <b>{chat_entity}</b>\n<b>Что-то пошло не так:</b>\n<code>{ex}</code>",
        reply_markup=get_markup(is_last),
    )

async def error_handler_delete_chat(ex: Exception, message: types.Message, chat_entity: str, is_last: bool):
    logger.error(f"Что-то пошло не так при удалении чата {ex}")

    await message.reply(
        f"Чат: <b>{chat_entity}</b>\n<b>Что-то пошло не так:</b>\n<code>{ex}</code>",
    )
