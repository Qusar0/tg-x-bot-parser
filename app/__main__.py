import os
import asyncio
import traceback
import app.config  # noqa
from loguru import logger


async def main():

    from app.xscrapper import xscrapper
    from app.database.redis import redis_store
    from app.database.connection import init_connection, close_connection
    from app.cleanup_scheduler import cleanup_scheduler

    await init_connection()
    await redis_store.connect()

    try:
        if os.environ["APP_CLIENT"] == "xscrapper":
            await xscrapper.start()

        elif os.environ["APP_CLIENT"] == "bot":
            from app.bot import run_bot
            from app.userbot.userbot_manager import userbot_manager

            # Запускаем планировщик очистки для бота
            await cleanup_scheduler.start()

            await asyncio.gather(
                *[
                    userbot_manager.start(),
                    run_bot(),
                ],
            )

    except Exception as ex:
        logger.error(f"Глобальная ошибка: {ex}")
        print(traceback.print_exc())
    finally:
        # Останавливаем планировщик очистки
        await cleanup_scheduler.stop()
        await close_connection()
        await redis_store.disconnect()


if __name__ == "__main__":
    logger.add(
        "logs/debug.log",
        level="DEBUG",
        format="{time} | {level} | {function}:{line} | {message}",
        rotation="4096 KB",
        compression="zip",
    )

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Вышли из программы")
