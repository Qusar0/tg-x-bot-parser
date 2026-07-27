import os
import json
from dataclasses import dataclass
from dataclasses_json import dataclass_json

default_data = {
    "central_chats": [],
    "admins": [],
    "scrapper_page_sleep_sec": 60 * 5,
    "scrapper_more_posts_clicks_count": 5,
    "x_channels_min_rating": 0,
    "source_tg": True,
    "source_x": True,
    "poller_enabled": True,
    "poller_interval_sec": 300,
    "poller_limit": 50,
    "poller_channel_delay_sec": 2,
    "poller_max_age_sec": 3600,
}
filename = "settings.json"


@dataclass_json
@dataclass
class CentralChat:
    chat_id: int
    title: str
    entity: str = ""


class Settings:
    _instance = None

    def __new__(cls):
        if not cls._instance:
            # if os.environ.get("APP_MODE") == "dev" and os.path.exists(filename):
            #     os.remove(filename)

            cls._instance = super().__new__(cls)
            cls._instance.filename = filename
            cls._instance._load_settings()

        return cls._instance

    def _load_settings(self):
        if not os.path.exists(self.filename):
            # Создаем новый файл с начальными значениями по умолчанию
            self.settings = default_data
            self._save_settings()
        else:
            with open(self.filename) as f:
                loaded = json.load(f)

            # Сливаем с дефолтами: значения из файла имеют приоритет, а ключи,
            # появившиеся в default_data после создания файла (например,
            # новые настройки поллера), доезжают до settings.json, а не
            # остаются доступны только через .get() с дефолтом в геттерах.
            self.settings = {**default_data, **loaded}
            self._save_settings()

    def _save_settings(self):
        with open(self.filename, "w") as f:
            json.dump(self.settings, f, indent=4)

    def get_admins(self) -> list[int]:
        return self.settings["admins"]

    def get_poller_enabled(self) -> bool:
        return bool(self.settings.get("poller_enabled", True))

    def get_poller_interval_sec(self) -> int:
        return int(self.settings.get("poller_interval_sec", 300))

    def get_poller_limit(self) -> int:
        return int(self.settings.get("poller_limit", 50))

    def get_poller_channel_delay_sec(self) -> int:
        return int(self.settings.get("poller_channel_delay_sec", 2))

    def get_poller_max_age_sec(self) -> int:
        return int(self.settings.get("poller_max_age_sec", 3600))

    def get_template(self) -> str:
        return "🕹 Здравствуйте, добро пожаловать в панель управления:"

    def get_central_chats(self) -> list[CentralChat]:
        central_chats = self.settings["central_chats"]
        return [CentralChat.from_dict(chat) for chat in central_chats]

    def set_central_chats(self, central_chats: list[CentralChat]) -> None:
        self.settings["central_chats"] = [chat.to_dict() for chat in central_chats]
        self._save_settings()

    def add_central_chat(self, chat_id: int, chat_title: str, chat_entity: str = None) -> CentralChat:
        central_chat = CentralChat(chat_id=chat_id, title=chat_title, entity=chat_entity)
        central_chats = self.get_central_chats()

        if chat_id not in [chat.chat_id for chat in central_chats]:
            central_chats.append(central_chat)

        self.set_central_chats(central_chats)

    def remove_central_chat(self, chat_id: int):
        central_chats = list(filter(lambda chat: chat.chat_id != chat_id, self.get_central_chats()))
        self.set_central_chats(central_chats)

    def get_scrapper_page_sleep_sec(self) -> int:
        return self.settings["scrapper_page_sleep_sec"]

    def get_scrapper_more_posts_clicks_count(self) -> int:
        return self.settings["scrapper_more_posts_clicks_count"]

    def get_x_channels_min_rating(self) -> int:
        return self.settings.get("x_channels_min_rating", 0)

    def set_x_channels_min_rating(self, rating: int) -> None:
        self.settings["x_channels_min_rating"] = rating
        self._save_settings()

    def get_source_tg(self) -> bool:
        return self.settings.get("source_tg", True)

    def set_source_tg(self, value: bool) -> None:
        self.settings["source_tg"] = bool(value)
        self._save_settings()

    def get_source_x(self) -> bool:
        return self.settings.get("source_x", True)

    def set_source_x(self, value: bool) -> None:
        self.settings["source_x"] = bool(value)
        self._save_settings()


settings = Settings()
