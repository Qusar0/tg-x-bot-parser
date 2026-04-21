from aiogram import types
from aiogram.filters import Command
from app.bot.routers.admin.tg_parser.errors import NoPostsProvided
from app.bot.routers.admin.tg_parser.signals_parser_4_n8n import ChannelHistoryParser
from loguru import logger

from app.bot.routers.admin import admin_router
from app.bot.utils.n8n_client import N8NClient


@admin_router.message(Command("check"))
async def check_channel_handler(message: types.Message):
    text = (message.text or "").strip()
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "⚠️ Укажи канал в формате:\n<code>/check @channel</code>"
        )
        return

    channel = parts[1].strip()
    if not channel.startswith("@"):
        await message.answer("⚠️ Канал должен быть в формате <code>@channel</code>")
        return

    logger.info(
        "Команда /check вызвана | user_id={} | username=@{} | channel={}",
        message.from_user.id,
        message.from_user.username or "unknown",
        channel,
    )

    await message.answer(
        f"🕐 Проверка канала <code>{channel}</code> запущена\n"
        f"⏳ Выполняю сбор постов..."
    )

    posts = None
    try:
        async with ChannelHistoryParser() as parser:
            posts = await parser.get_last_posts(channel=channel, limit=25, load_media_binary=False)

            posts_payload = []
            media_files = {}
            for post_obj in posts:
                post = parser.make_post_obj_sendable(post_obj)
                if post['media_filename'] is not None:
                    media_filename = post['media_filename']
                    media_files[media_filename] = post_obj.media.content

                posts_payload.append(post)
            
            await message.answer(
                f"🕒 Сбор постов канала <code>{channel}</code> завершен\n"
                f"\tУспешно собрано {len(posts)} сообщений\n"
                f"⏳ Запускаю проверку постов..."
            )

    except Exception as ex:
        logger.exception("Ошибка при парсинге постов для /check")

        await message.answer(
            f"❌ Не удалось получить посты канала\n"
            f"<code>{ex}</code>"
        )
    
    try:
        if posts is None:
            raise NoPostsProvided

        client = N8NClient()
        result = await client.send_posts_batch(
            channel=channel,
            posts=posts_payload,
            media_files=media_files,
            from_id=message.from_user.id,
        )
    
        request_id = result.get("request_id")

        await message.answer(
            f"🕖 Проверка постов канала <code>{channel}</code> запущена\n"
            f"🆔 request_id: <code>{request_id}</code>\n"
            f"⏳ Результат будет отправлен отдельным сообщением после завершения обработки"
        )

        # stub_winrate = result.get("stub_winrate", "N/A")

        # await message.answer(
        #     f"✅ Проверка постов канала <code>{channel}</code> завершена\n"
        #     f"\tn8n ответил успешно\n"
        #     f"\tstub_winrate: {stub_winrate}% (Общее кол-во постов: {len(posts)})"
        # )

    except NoPostsProvided as ex:
        logger.exception("Невозможно проанализировать посты, так как они не были предоставлены")
    except Exception as ex:
        logger.exception("Ошибка при вызове n8n для /check")

        await message.answer(
            f"❌ Не удалось получить ответ от n8n\n"
            f"<code>{ex}</code>"
        )
