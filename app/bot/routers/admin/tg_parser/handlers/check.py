from aiogram import types
from aiogram.filters import Command
from loguru import logger

from app.bot.routers.admin import admin_router


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
        f"✅ Команда принята. Канал: <code>{channel}</code>\n"
        f"Пока что только логирую вызов."
    )
