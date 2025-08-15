from aiogram import Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from app.bot.utils.Bot import Bot
from app.config import config

bot = Bot(token=config.bot.token, default=DefaultBotProperties(parse_mode="html", link_preview_is_disabled=True))
dispatcher = Dispatcher(storage=RedisStorage.from_url(config.redis.uri))
