import asyncio
from aiogram import exceptions
from aiogram import Bot as AiogramBot


class Bot(AiogramBot):
    async def __call__(self, *args, **kwargs):
        while True:
            try:
                return await super().__call__(*args, **kwargs)
            except exceptions.TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after)
