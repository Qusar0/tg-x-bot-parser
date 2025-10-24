import time
import os
import configparser
import argparse
import logging
import random
from loguru import logger
from dataclasses import dataclass


@dataclass
class DbConfig:
    name: str
    uri: str


@dataclass
class Userbot:
    api_id: int  # noqa
    api_hash: str
    phone_number: str


@dataclass
class Bot:
    token: str
    admins: list[str]


@dataclass
class Redis:
    host: str
    port: int
    uri: str


@dataclass
class Config:
    bot: Bot
    userbot: Userbot
    db: DbConfig
    redis: Redis

    def get_sleep_time(self) -> int:
        return random.randint(120, 200)


config = configparser.ConfigParser()


def check_values():
    # Проверка наличия секции и полей
    try:
        assert "bot" in config.sections(), "Отсутствует секция [bot] в конфигурационном файле"
        assert config.get("bot", "token"), "Отсутствует значение token в конфигурационном файле"

        assert "userbot" in config.sections(), "Отсутствует секция [userbot] в конфигурационном файле"
        assert config.get("userbot", "api_id"), "Отсутствует значение api_id в конфигурационном файле"
        assert config.get("userbot", "api_hash"), "Отсутствует значение api_hash в конфигурационном файле"
        assert config.get("userbot", "phone_number"), "Отсутствует значение phone_number в конфигурационном файле"

        assert "redis" in config.sections(), "Отсутствует секция [redis] в конфигурационном файле"
        assert config.get("redis", "host"), "Отсутствует значение host в конфигурационном файле"
        assert config.get("redis", "port"), "Отсутствует значение port в конфигурационном файле"

        assert "database" in config.sections(), "Отсутствует секция [database] в конфигурационном файле"
        assert config.get("database", "name"), "Отсутствует значение name в конфигурационном файле"

    except AssertionError as e:
        print("Ошибка:", e)
        time.sleep(10)  # Задержка на 10 секунд
        exit()


def load_config():
    mode = os.environ.get("APP_MODE")
    path = f"./config.{mode}.ini"
    logger.info(f"Конфиг загружен: {path}")
    config.read(path, encoding="utf-8")
    check_values()

    userbot = config["userbot"]
    database_name = config["database"]["name"]
    bot = config["bot"]
    redis = config["redis"]

    return Config(
        bot=Bot(
            token=bot["token"],
            admins=[int(admin.strip()) for admin in bot["admins"].split(",")],
        ),
        userbot=Userbot(
            api_id=userbot["api_id"],
            api_hash=userbot["api_hash"],
            phone_number=userbot["phone_number"],
        ),
        redis=Redis(
            host=redis["host"],
            port=redis["port"],
            uri=f"redis://{redis['host']}:{redis['port']}",
        ),
        db=DbConfig(name=database_name, uri=f"sqlite://{database_name}.db"),
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Управление режимом работы приложения")
    parser.add_argument("--mode", choices=["dev", "prod"], required=True, help="Режим работы приложения")
    parser.add_argument("--client", choices=["bot", "scrapper", "xscrapper"], required=True, help="Тип клиента для запуска")
    args = parser.parse_args()
    os.environ["APP_MODE"] = args.mode
    os.environ["APP_CLIENT"] = args.client

    if args.mode == "dev":
        logging.basicConfig(level=logging.INFO)

    return args


if not (os.environ.get("APP_MODE") and os.environ.get("APP_CLIENT")):
    parse_arguments()

config = load_config()
