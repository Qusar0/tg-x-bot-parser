from loguru import logger
from tortoise import Tortoise
from . import TORTOISE_ORM


async def init_connection():
    await Tortoise.init(TORTOISE_ORM)
    await Tortoise.generate_schemas()
    logger.success("Подключились к базе данных")


async def close_connection():
    await Tortoise.close_connections()
