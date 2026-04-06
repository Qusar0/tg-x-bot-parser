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
        f"⏳ Запускаю проверку..."
    )

    # return {
    #     "ok": True,
    #     "channel": channel,
    #     "posts_count": len(posts),
    #     "posts": posts,
    # }

    client = N8NClient()
    try:
        
        async with ChannelHistoryParser() as parser:
            posts = await parser.get_last_posts(channel=channel, limit=5)
            # /check @cryptosignal

            result = await client.check_channel(
                channel=channel,
                requested_by=message.from_user.id,
                chat_id=message.chat.id,
                # posts=posts
            )
        
            stub_winrate = result.get("stub_winrate", "N/A")

            await message.answer(
                f"✅ Проверка канала <code>{channel}</code> завершена\n"
                f"n8n ответил успешно\n"
                f"stub_winrate: {stub_winrate}%"
            )
    except Exception as ex:
        logger.exception("Ошибка при вызове n8n для /check")

        await message.answer(
            f"❌ Не удалось получить ответ от n8n\n"
            f"<code>{ex}</code>"
        )
