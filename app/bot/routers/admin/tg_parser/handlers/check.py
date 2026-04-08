from aiogram import types
from aiogram.filters import Command
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
        f"✅ Проверка канала <code>{channel}</code> запущена\n"
        f"⏳ Выполняю сбор постов..."
    )

    client = N8NClient()
    try:
        
        async with ChannelHistoryParser() as parser:
            posts = await parser.get_last_posts(channel=channel, limit=10, load_media_binary=True)
            # /check @cryptosignal

            posts_payload = []
            media_files = {}
            for post_obj in posts:
                media_filename = None

                if post_obj.media:
                    media_filename = f"media/{post_obj.media.filename}"
                    media_files[media_filename] = post_obj.media.content

                post = {
                    "message_id": post_obj.message_id,
                    "date": post_obj.date,
                    "chat_id": post_obj.chat_id,
                    "chat_title": post_obj.chat_title,
                    "chat_username": post_obj.chat_username,
                    "text": post_obj.text,
                    "caption": post_obj.caption,
                    "has_photo": post_obj.has_photo,
                    "has_video": post_obj.has_video,
                    "has_document": post_obj.has_document,
                    "media_type": post_obj.media_type,
                    "media_filename": media_filename,
                }

                posts_payload.append(post)
            
            await message.answer(
                f"✅ Сбор постов канала <code>{channel}</code> завершен\n"
                f"\tУспешно собрано {len(posts)} сообщений\n"
                f"⏳ Запускаю проверку постов..."
            )

            result = await client.send_posts_batch(
                channel=channel,
                posts=posts_payload,
                media_files=media_files,
            )
        
            stub_winrate = result.get("stub_winrate", "N/A")

            await message.answer(
                f"✅ Проверка постов канала <code>{channel}</code> завершена\n"
                f"\tn8n ответил успешно\n"
                f"\tstub_winrate: {stub_winrate}% (Общее кол-во постов: {len(posts)})"
            )
    except Exception as ex:
        logger.exception("Ошибка при вызове n8n для /check")

        await message.answer(
            f"❌ Не удалось получить ответ от n8n\n"
            f"<code>{ex}</code>"
        )
