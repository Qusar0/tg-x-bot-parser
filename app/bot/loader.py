from aiogram import Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from app.bot.utils.Bot import Bot
from app.config import config


session = AiohttpSession(proxy=config.proxy.url)
bot = Bot(token=config.bot.token, default=DefaultBotProperties(parse_mode="html", link_preview_is_disabled=True), session=session)
dispatcher = Dispatcher(storage=RedisStorage.from_url(config.redis.uri))
