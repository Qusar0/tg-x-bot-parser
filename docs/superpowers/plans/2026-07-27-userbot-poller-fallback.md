# Userbot Poller Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить поллер, который периодически читает историю мониторинг-каналов через `get_chat_history` и отдаёт новые сообщения в существующий обработчик, чтобы посты доходили даже когда push-апдейты Telegram по каналу не приходят.

**Architecture:** Поллер — асинхронная задача внутри процесса `bot`, использующая уже залогиненный клиент `userbot_manager.client`. Позиции чтения и отметки обработанных сообщений хранятся в Redis под префиксом `poller:`. Вся обработка (привязки, ключи, стоп-слова, отправка) переиспользует существующий `Handlers.message_handler` — логика фильтрации не меняется.

**Tech Stack:** Python 3.11+, pyrogram 2.x, redis.asyncio, tortoise-orm, loguru, pytest + pytest-asyncio.

## Global Constraints

- Логи пишутся через `loguru`, текст сообщений — на русском, в стиле существующих логов проекта.
- Все новые ключи Redis начинаются с префикса `poller:` — существующая чистка `cleanup_old_posts` удаляет только `post:*` и не должна их задевать.
- Геттеры настроек читают значения через `self.settings.get(ключ, дефолт)` — боевой `settings.json` создан до этой задачи и не содержит новых ключей; прямое индексирование уронит бота.
- Логика фильтрации и маршрутизации (ключи, стоп-слова, привязки к центральным чатам) в этой задаче не меняется.
- X-скраппер (`app/xscrapper/`) в этой задаче не затрагивается.
- Модули `poller.py` и `poller_state.py` не импортируют на уровне модуля ничего, кроме `asyncio`, `loguru` и `pyrogram.errors`. Все обращения к `app.config`, `app.database.*`, `app.settings`, `app.userbot.userbot_manager`, `app.userbot.handlers` — только лениво, внутри функций.
- Тесты не обращаются к реальным Telegram и Redis — зависимости подменяются фейками через конструктор `ChannelPoller` или `monkeypatch`.

**Среда разработки — проверено на этой машине:**

- Установлены только `loguru` и `pyrogram`. Отсутствуют `tortoise`, `redis`, `aiogram`,
  `bs4`, `dataclasses_json`. Устанавливать их не требуется.
- Импорт `app.config` на уровне модуля завершает процесс: при отсутствии `config.dev.ini`
  функция `check_values()` вызывает `exit()`. Поэтому цепочка
  `app.userbot.handlers → app.bot.Manager → app.bot.loader → app.config` в тестах
  недопустима, а `app.settings` тянет отсутствующий `dataclasses_json`.
- Из-за этого все внешние зависимости поллера инъектируются через конструктор, включая
  настройки. Тесты запускаются без установки зависимостей проекта.
- В проекте нет файлов `__init__.py` — пакеты неявные (namespace packages). Для `tests/`
  файл `__init__.py` создаётся, чтобы работал импорт `from tests.fakes import ...`.

---

### Task 1: Хранилище состояния поллера в Redis

**Files:**
- Create: `app/userbot/poller_state.py`
- Create: `tests/__init__.py`
- Create: `tests/test_poller_state.py`
- Create: `pytest.ini`
- Modify: `requirements.txt`

**Interfaces:**
- Consumes: `app.database.redis.redis_store` (методы `get_value`, `set_value`, `set_value_ex`)
- Produces:
  - `async get_last_id(chat_id: int) -> int | None`
  - `async set_last_id(chat_id: int, message_id: int) -> None`
  - `async is_seen(chat_id: int, message_id: int) -> bool`
  - `async mark_seen(chat_id: int, message_id: int) -> None`
  - `async is_group_sent(chat_id: int, media_group_id: str) -> bool`
  - `async mark_group_sent(chat_id: int, media_group_id: str) -> None`
  - модульная переменная `_store` — точка подмены хранилища в тестах
  - константа `SEEN_TTL_SEC = 172800`

- [ ] **Step 1: Добавить тестовые зависимости**

В `requirements.txt` добавить в конец файла:

```
pytest==8.3.4
pytest-asyncio==0.24.0
```

Создать `pytest.ini`:

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

Установить локально:

```bash
pip install pytest==8.3.4 pytest-asyncio==0.24.0
```

- [ ] **Step 2: Написать падающие тесты**

Создать пустой `tests/__init__.py`.

Создать `tests/test_poller_state.py`:

```python
import pytest

from app.userbot import poller_state


class FakeRedisStore:
    """Фейковое хранилище с интерфейсом RedisStore."""

    def __init__(self):
        self.data = {}
        self.ttls = {}

    async def get_value(self, key: str):
        return self.data.get(key)

    async def set_value(self, key: str, value: str):
        self.data[key] = value

    async def set_value_ex(self, key: str, value: str, expire_sec: int):
        self.data[key] = value
        self.ttls[key] = expire_sec


@pytest.fixture
def store(monkeypatch):
    fake = FakeRedisStore()
    monkeypatch.setattr(poller_state, "_store", fake)
    return fake


async def test_get_last_id_returns_none_when_missing(store):
    assert await poller_state.get_last_id(-100500) is None


async def test_set_and_get_last_id(store):
    await poller_state.set_last_id(-100500, 42)

    assert await poller_state.get_last_id(-100500) == 42
    assert store.data["poller:last_id:-100500"] == "42"


async def test_get_last_id_returns_none_on_broken_value(store):
    store.data["poller:last_id:-100500"] = "не число"

    assert await poller_state.get_last_id(-100500) is None


async def test_seen_marks_message_with_ttl(store):
    assert await poller_state.is_seen(-100500, 7) is False

    await poller_state.mark_seen(-100500, 7)

    assert await poller_state.is_seen(-100500, 7) is True
    assert store.ttls["poller:seen:-100500:7"] == poller_state.SEEN_TTL_SEC


async def test_group_sent_marks_album_with_ttl(store):
    assert await poller_state.is_group_sent(-100500, "13835058055") is False

    await poller_state.mark_group_sent(-100500, "13835058055")

    assert await poller_state.is_group_sent(-100500, "13835058055") is True
    assert store.ttls["poller:group:-100500:13835058055"] == poller_state.SEEN_TTL_SEC
```

- [ ] **Step 3: Запустить тесты и убедиться, что они падают**

Run: `python -m pytest tests/test_poller_state.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.userbot.poller_state'`

- [ ] **Step 4: Реализовать модуль**

Создать `app/userbot/poller_state.py`:

```python
"""Состояние поллера в Redis: позиции чтения и отметки обработанных сообщений.

Ключи вынесены под префикс poller:, чтобы чистка старых постов
(cleanup_old_posts удаляет post:*) их не задевала.
"""
from loguru import logger

LAST_ID_KEY = "poller:last_id:{chat_id}"
SEEN_KEY = "poller:seen:{chat_id}:{message_id}"
GROUP_KEY = "poller:group:{chat_id}:{media_group_id}"

SEEN_TTL_SEC = 48 * 60 * 60

# Подменяется в тестах; в бою резолвится лениво, чтобы не тянуть app.config при импорте
_store = None


def _get_store():
    if _store is not None:
        return _store

    from app.database.redis import redis_store

    return redis_store


async def get_last_id(chat_id: int) -> int | None:
    value = await _get_store().get_value(LAST_ID_KEY.format(chat_id=chat_id))
    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        logger.warning(f"Поллер: некорректная позиция для чата {chat_id}: {value!r}")
        return None


async def set_last_id(chat_id: int, message_id: int) -> None:
    await _get_store().set_value(LAST_ID_KEY.format(chat_id=chat_id), str(message_id))


async def is_seen(chat_id: int, message_id: int) -> bool:
    key = SEEN_KEY.format(chat_id=chat_id, message_id=message_id)
    return await _get_store().get_value(key) is not None


async def mark_seen(chat_id: int, message_id: int) -> None:
    key = SEEN_KEY.format(chat_id=chat_id, message_id=message_id)
    await _get_store().set_value_ex(key, "1", SEEN_TTL_SEC)


async def is_group_sent(chat_id: int, media_group_id: str) -> bool:
    key = GROUP_KEY.format(chat_id=chat_id, media_group_id=media_group_id)
    return await _get_store().get_value(key) is not None


async def mark_group_sent(chat_id: int, media_group_id: str) -> None:
    key = GROUP_KEY.format(chat_id=chat_id, media_group_id=media_group_id)
    await _get_store().set_value_ex(key, "1", SEEN_TTL_SEC)
```

- [ ] **Step 5: Запустить тесты и убедиться, что они проходят**

Run: `python -m pytest tests/test_poller_state.py -v`
Expected: PASS, 5 passed

- [ ] **Step 6: Коммит**

```bash
git add requirements.txt pytest.ini tests/__init__.py tests/test_poller_state.py app/userbot/poller_state.py
git commit -m "Поллер: хранилище позиций и отметок в Redis"
```

---

### Task 2: Чтение одного канала (`poll_channel`)

**Files:**
- Create: `app/userbot/poller.py`
- Create: `tests/fakes.py`
- Create: `tests/test_poller_channel.py`

**Interfaces:**
- Consumes: интерфейс `poller_state` из Task 1 (`get_last_id`, `set_last_id`, `is_seen`)
- Produces:
  - `class ChannelPoller` с конструктором
    `ChannelPoller(client=None, handler=None, chats_provider=None, state=None, sleep=None, settings=None)`
  - `async ChannelPoller.poll_channel(chat_id: int, limit: int) -> int` — возвращает число обработанных сообщений

- [ ] **Step 1: Написать фейки**

Создать `tests/fakes.py`:

```python
"""Фейки для тестов поллера: без реальных Telegram и Redis."""


class FakeMessage:
    def __init__(self, message_id: int, chat_id: int, media_group_id=None):
        self.id = message_id
        self.chat = type("Chat", (), {"id": chat_id})()
        self.media_group_id = media_group_id


class FakeClient:
    """История отдаётся свежими-первыми, как у pyrogram."""

    def __init__(self, history=None, error=None):
        self.history = history or {}
        self.error = error
        self.calls = []

    def get_chat_history(self, chat_id, limit=100):
        self.calls.append((chat_id, limit))
        error = self.error
        messages = list(self.history.get(chat_id, []))[:limit]

        async def generator():
            if error is not None:
                raise error
            for message in messages:
                yield message

        return generator()


class FakeState:
    def __init__(self, last_ids=None, seen=None, groups=None):
        self.last_ids = dict(last_ids or {})
        self.seen = set(seen or [])
        self.groups = set(groups or [])

    async def get_last_id(self, chat_id):
        return self.last_ids.get(chat_id)

    async def set_last_id(self, chat_id, message_id):
        self.last_ids[chat_id] = message_id

    async def is_seen(self, chat_id, message_id):
        return (chat_id, message_id) in self.seen

    async def mark_seen(self, chat_id, message_id):
        self.seen.add((chat_id, message_id))

    async def is_group_sent(self, chat_id, media_group_id):
        return (chat_id, media_group_id) in self.groups

    async def mark_group_sent(self, chat_id, media_group_id):
        self.groups.add((chat_id, media_group_id))


class RecordingHandler:
    def __init__(self, error=None):
        self.calls = []
        self.error = error

    async def __call__(self, client, message):
        self.calls.append(message.id)
        if self.error is not None:
            raise self.error
```

- [ ] **Step 2: Написать падающие тесты**

Создать `tests/test_poller_channel.py`:

```python
from app.userbot.poller import ChannelPoller
from tests.fakes import FakeClient, FakeMessage, FakeState, RecordingHandler

CHAT_ID = -1001297561296


def make_poller(history, state, handler):
    return ChannelPoller(
        client=FakeClient(history=history),
        handler=handler,
        state=state,
        sleep=_noop_sleep,
    )


async def _noop_sleep(_seconds):
    return None


async def test_bootstrap_records_position_without_processing():
    messages = [FakeMessage(105, CHAT_ID), FakeMessage(104, CHAT_ID)]
    state = FakeState()
    handler = RecordingHandler()
    poller = make_poller({CHAT_ID: messages}, state, handler)

    processed = await poller.poll_channel(CHAT_ID, limit=50)

    assert processed == 0
    assert handler.calls == []
    assert state.last_ids[CHAT_ID] == 105


async def test_new_messages_processed_in_chronological_order():
    messages = [FakeMessage(103, CHAT_ID), FakeMessage(102, CHAT_ID), FakeMessage(101, CHAT_ID)]
    state = FakeState(last_ids={CHAT_ID: 100})
    handler = RecordingHandler()
    poller = make_poller({CHAT_ID: messages}, state, handler)

    processed = await poller.poll_channel(CHAT_ID, limit=50)

    assert processed == 3
    assert handler.calls == [101, 102, 103]
    assert state.last_ids[CHAT_ID] == 103


async def test_old_messages_are_not_processed():
    messages = [FakeMessage(100, CHAT_ID), FakeMessage(99, CHAT_ID)]
    state = FakeState(last_ids={CHAT_ID: 100})
    handler = RecordingHandler()
    poller = make_poller({CHAT_ID: messages}, state, handler)

    processed = await poller.poll_channel(CHAT_ID, limit=50)

    assert processed == 0
    assert handler.calls == []


async def test_seen_message_is_skipped_but_position_advances():
    messages = [FakeMessage(102, CHAT_ID), FakeMessage(101, CHAT_ID)]
    state = FakeState(last_ids={CHAT_ID: 100}, seen={(CHAT_ID, 101)})
    handler = RecordingHandler()
    poller = make_poller({CHAT_ID: messages}, state, handler)

    processed = await poller.poll_channel(CHAT_ID, limit=50)

    assert processed == 1
    assert handler.calls == [102]
    assert state.last_ids[CHAT_ID] == 102


async def test_handler_error_does_not_stop_remaining_messages():
    messages = [FakeMessage(102, CHAT_ID), FakeMessage(101, CHAT_ID)]
    state = FakeState(last_ids={CHAT_ID: 100})
    handler = RecordingHandler(error=RuntimeError("боевой сбой"))
    poller = make_poller({CHAT_ID: messages}, state, handler)

    processed = await poller.poll_channel(CHAT_ID, limit=50)

    assert processed == 0
    assert handler.calls == [101, 102]
    assert state.last_ids[CHAT_ID] == 102


async def test_limit_is_passed_to_client():
    messages = [FakeMessage(101, CHAT_ID)]
    state = FakeState(last_ids={CHAT_ID: 100})
    handler = RecordingHandler()
    client = FakeClient(history={CHAT_ID: messages})
    poller = ChannelPoller(client=client, handler=handler, state=state, sleep=_noop_sleep)

    await poller.poll_channel(CHAT_ID, limit=25)

    assert client.calls == [(CHAT_ID, 25)]
```

- [ ] **Step 3: Запустить тесты и убедиться, что они падают**

Run: `python -m pytest tests/test_poller_channel.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.userbot.poller'`

- [ ] **Step 4: Реализовать `ChannelPoller.poll_channel`**

Создать `app/userbot/poller.py`:

```python
"""Поллер мониторинг-каналов.

Периодически читает историю каналов через get_chat_history и отдаёт новые
сообщения в существующий обработчик. Нужен там, где push-апдейты Telegram
по каналу не приходят.
"""
import asyncio

from loguru import logger


class ChannelPoller:
    def __init__(
        self,
        client=None,
        handler=None,
        chats_provider=None,
        state=None,
        sleep=None,
        settings=None,
    ):
        self._client = client
        self._handler = handler
        self._chats_provider = chats_provider
        self._state = state
        self._settings = settings
        self._sleep = sleep or asyncio.sleep

    def _get_client(self):
        if self._client is not None:
            return self._client

        from app.userbot.userbot_manager import userbot_manager

        return userbot_manager.client

    def _get_handler(self):
        if self._handler is not None:
            return self._handler

        from app.userbot.handlers import Handlers

        return Handlers.message_handler

    def _get_state(self):
        if self._state is not None:
            return self._state

        from app.userbot import poller_state

        return poller_state

    def _get_settings(self):
        if self._settings is not None:
            return self._settings

        from app.settings import settings

        return settings

    async def poll_channel(self, chat_id: int, limit: int) -> int:
        """Читает новые сообщения канала и отдаёт их в обработчик."""
        client = self._get_client()
        state = self._get_state()

        last_id = await state.get_last_id(chat_id)

        if last_id is None:
            newest_id = None
            async for message in client.get_chat_history(chat_id, limit=1):
                newest_id = message.id

            if newest_id is None:
                logger.info(f"Поллер: канал {chat_id} — история пуста, позиция не установлена")
                return 0

            await state.set_last_id(chat_id, newest_id)
            logger.info(
                f"Поллер: канал {chat_id} — первая инициализация, "
                f"стартовая позиция {newest_id}, старые сообщения не отправляем"
            )
            return 0

        new_messages = []
        reached_last = False
        async for message in client.get_chat_history(chat_id, limit=limit):
            if message.id <= last_id:
                reached_last = True
                break
            new_messages.append(message)

        if not new_messages:
            return 0

        if not reached_last and len(new_messages) >= limit:
            logger.warning(
                f"Поллер: канал {chat_id} — выбран лимит {limit} сообщений, "
                f"часть постов могла быть пропущена"
            )

        new_messages.reverse()

        handler = self._get_handler()
        processed = 0
        max_id = last_id

        for message in new_messages:
            max_id = max(max_id, message.id)

            if await state.is_seen(chat_id, message.id):
                continue

            try:
                await handler(client, message)
                processed += 1
            except Exception as ex:
                logger.error(
                    f"Поллер: ошибка обработки сообщения {message.id} канала {chat_id}: {ex}"
                )

        await state.set_last_id(chat_id, max_id)

        if processed:
            logger.info(f"Поллер: канал {chat_id} — обработано новых сообщений: {processed}")

        return processed
```

- [ ] **Step 5: Запустить тесты и убедиться, что они проходят**

Run: `python -m pytest tests/test_poller_channel.py -v`
Expected: PASS, 6 passed

- [ ] **Step 6: Коммит**

```bash
git add app/userbot/poller.py tests/fakes.py tests/test_poller_channel.py
git commit -m "Поллер: чтение новых сообщений канала с bootstrap и дедупом"
```

---

### Task 3: Обход каналов, цикл и настройки

**Files:**
- Modify: `app/settings.py`
- Modify: `app/userbot/poller.py`
- Create: `tests/test_poller_loop.py`

**Interfaces:**
- Consumes: `ChannelPoller.poll_channel(chat_id, limit)` из Task 2
- Produces:
  - `async ChannelPoller.poll_once() -> int` — один полный обход всех каналов
  - `async ChannelPoller.start() -> None` — бесконечный цикл с интервалом
  - модульный синглтон `channel_poller = ChannelPoller()`
  - `settings.get_poller_enabled() -> bool`, `settings.get_poller_interval_sec() -> int`,
    `settings.get_poller_limit() -> int`, `settings.get_poller_channel_delay_sec() -> int`

- [ ] **Step 1: Добавить настройки**

В `app/settings.py` в словарь `default_data` добавить четыре ключа после `"source_x": True,`:

```python
    "poller_enabled": True,
    "poller_interval_sec": 300,
    "poller_limit": 50,
    "poller_channel_delay_sec": 2,
```

В класс `Settings` после метода `get_admins` добавить геттеры. Значения читаются через
`.get()` с дефолтом — боевой `settings.json` создан раньше и новых ключей не содержит:

```python
    def get_poller_enabled(self) -> bool:
        return bool(self.settings.get("poller_enabled", True))

    def get_poller_interval_sec(self) -> int:
        return int(self.settings.get("poller_interval_sec", 300))

    def get_poller_limit(self) -> int:
        return int(self.settings.get("poller_limit", 50))

    def get_poller_channel_delay_sec(self) -> int:
        return int(self.settings.get("poller_channel_delay_sec", 2))
```

- [ ] **Step 2: Написать падающие тесты**

Создать `tests/test_poller_loop.py`:

```python
from pyrogram.errors import FloodWait

from app.userbot.poller import ChannelPoller
from tests.fakes import FakeClient, FakeMessage, FakeState, RecordingHandler

CHAT_A = -1001297561296
CHAT_B = -1001727857237


class FakeChat:
    def __init__(self, telegram_id):
        self.telegram_id = telegram_id


class FakeSettings:
    """Настройки поллера без обращения к app.settings."""

    def __init__(self, enabled=True, interval=300, limit=50, delay=2):
        self._enabled = enabled
        self._interval = interval
        self._limit = limit
        self._delay = delay

    def get_poller_enabled(self):
        return self._enabled

    def get_poller_interval_sec(self):
        return self._interval

    def get_poller_limit(self):
        return self._limit

    def get_poller_channel_delay_sec(self):
        return self._delay


class SleepRecorder:
    def __init__(self):
        self.calls = []

    async def __call__(self, seconds):
        self.calls.append(seconds)


def make_chats_provider(chat_ids):
    async def provider():
        return [FakeChat(chat_id) for chat_id in chat_ids]

    return provider


async def test_poll_once_walks_all_channels():
    history = {
        CHAT_A: [FakeMessage(101, CHAT_A)],
        CHAT_B: [FakeMessage(201, CHAT_B)],
    }
    state = FakeState(last_ids={CHAT_A: 100, CHAT_B: 200})
    handler = RecordingHandler()
    poller = ChannelPoller(
        client=FakeClient(history=history),
        handler=handler,
        chats_provider=make_chats_provider([CHAT_A, CHAT_B]),
        state=state,
        sleep=SleepRecorder(),
        settings=FakeSettings(),
    )

    total = await poller.poll_once()

    assert total == 2
    assert sorted(handler.calls) == [101, 201]


async def test_poll_once_pauses_between_channels():
    state = FakeState(last_ids={CHAT_A: 100, CHAT_B: 200})
    sleeper = SleepRecorder()
    poller = ChannelPoller(
        client=FakeClient(history={}),
        handler=RecordingHandler(),
        chats_provider=make_chats_provider([CHAT_A, CHAT_B]),
        state=state,
        sleep=sleeper,
        settings=FakeSettings(),
    )

    await poller.poll_once()

    assert len(sleeper.calls) == 2


async def test_channel_error_does_not_stop_the_walk():
    state = FakeState(last_ids={CHAT_A: 100, CHAT_B: 200})
    handler = RecordingHandler()

    class BrokenForFirstChat(FakeClient):
        def get_chat_history(self, chat_id, limit=100):
            if chat_id == CHAT_A:
                raise ValueError("канал недоступен")
            return super().get_chat_history(chat_id, limit=limit)

    client = BrokenForFirstChat(history={CHAT_B: [FakeMessage(201, CHAT_B)]})
    poller = ChannelPoller(
        client=client,
        handler=handler,
        chats_provider=make_chats_provider([CHAT_A, CHAT_B]),
        state=state,
        sleep=SleepRecorder(),
        settings=FakeSettings(),
    )

    total = await poller.poll_once()

    assert total == 1
    assert handler.calls == [201]


async def test_floodwait_is_awaited_and_walk_continues():
    state = FakeState(last_ids={CHAT_A: 100, CHAT_B: 200})
    handler = RecordingHandler()
    sleeper = SleepRecorder()

    class FloodOnFirstChat(FakeClient):
        def get_chat_history(self, chat_id, limit=100):
            if chat_id == CHAT_A:
                raise FloodWait(value=17)
            return super().get_chat_history(chat_id, limit=limit)

    client = FloodOnFirstChat(history={CHAT_B: [FakeMessage(201, CHAT_B)]})
    poller = ChannelPoller(
        client=client,
        handler=handler,
        chats_provider=make_chats_provider([CHAT_A, CHAT_B]),
        state=state,
        sleep=sleeper,
        settings=FakeSettings(),
    )

    total = await poller.poll_once()

    assert total == 1
    assert 17 in sleeper.calls
```

- [ ] **Step 3: Запустить тесты и убедиться, что они падают**

Run: `python -m pytest tests/test_poller_loop.py -v`
Expected: FAIL — `AttributeError: 'ChannelPoller' object has no attribute 'poll_once'`

- [ ] **Step 4: Реализовать обход и цикл**

В `app/userbot/poller.py` добавить импорт ошибки после существующих импортов.
Настройки на уровне модуля не импортируются — только лениво через `_get_settings()`:

```python
from pyrogram.errors import FloodWait
```

Добавить метод получения списка каналов рядом с остальными `_get_*`:

```python
    async def _get_chats(self):
        if self._chats_provider is not None:
            return await self._chats_provider()

        from app.database.repo.Chat import ChatRepo

        return await ChatRepo.get_monitoring_chats()
```

Добавить в конец класса `ChannelPoller` два метода:

```python
    async def poll_once(self) -> int:
        """Один полный обход всех мониторинг-каналов."""
        chats = await self._get_chats()
        config = self._get_settings()
        limit = config.get_poller_limit()
        delay = config.get_poller_channel_delay_sec()

        logger.info(f"Поллер: начинаем обход, каналов: {len(chats)}")

        total = 0
        for chat in chats:
            try:
                total += await self.poll_channel(chat.telegram_id, limit)
            except FloodWait as ex:
                logger.warning(
                    f"Поллер: FloodWait {ex.value} сек на канале {chat.telegram_id}, ждём"
                )
                await self._sleep(ex.value)
            except Exception as ex:
                logger.warning(f"Поллер: канал {chat.telegram_id} недоступен: {ex}")

            await self._sleep(delay)

        logger.info(f"Поллер: обход завершён, обработано сообщений: {total}")
        return total

    async def start(self) -> None:
        """Бесконечный цикл обходов с интервалом из настроек."""
        logger.info("Поллер: запущен")

        while True:
            config = self._get_settings()
            interval = config.get_poller_interval_sec()

            if not config.get_poller_enabled():
                await self._sleep(interval)
                continue

            client = self._get_client()
            if not getattr(client, "is_connected", False):
                logger.info("Поллер: userbot ещё не подключён, ждём следующей итерации")
                await self._sleep(interval)
                continue

            try:
                await self.poll_once()
            except Exception as ex:
                logger.error(f"Поллер: ошибка обхода: {ex}")

            await self._sleep(interval)
```

В конец файла добавить синглтон:

```python
channel_poller = ChannelPoller()
```

- [ ] **Step 5: Запустить все тесты и убедиться, что они проходят**

Run: `python -m pytest tests -v`
Expected: PASS, 15 passed

- [ ] **Step 6: Коммит**

```bash
git add app/settings.py app/userbot/poller.py tests/test_poller_loop.py
git commit -m "Поллер: обход каналов, цикл с интервалом и настройки"
```

---

### Task 4: Интеграция с обработчиком — отметки и однократная отправка альбомов

**Files:**
- Modify: `app/userbot/handlers.py`

**Interfaces:**
- Consumes: `poller_state.is_seen`, `poller_state.mark_seen`, `poller_state.is_group_sent`, `poller_state.mark_group_sent` из Task 1
- Produces: `async Handlers._send_to_central(chat_id: int, client, message, processed_text: str) -> None`

**Почему в этой задаче нет юнит-тестов.** Импорт `app.userbot.handlers` тянет цепочку
`app.bot.Manager → app.bot.loader → app.config`, а `app.config` при отсутствии
`config.dev.ini` вызывает `exit()` и убивает процесс pytest. Ставить полный набор
зависимостей проекта ради двух тестов нецелесообразно. Логика, которую здесь можно
сломать, — это семантика отметок `is_group_sent`/`mark_group_sent`, и она полностью
покрыта тестами Task 1. Изменения этой задачи проверяются компиляцией модуля и
пунктами 3-4 раздела «Проверка на проде».

- [ ] **Step 1: Добавить импорт состояния поллера**

В `app/userbot/handlers.py` в блок импортов добавить строку после
`from app.userbot.filters.is_word_match import is_word_match, get_matched_words`:

```python
from app.userbot import poller_state
```

- [ ] **Step 2: Добавить метод отправки с защитой от повторной отсылки альбома**

В класс `Handlers` сразу после метода `get_instance_id` добавить:

```python
    @staticmethod
    async def _send_to_central(chat_id: int, client, message, processed_text: str) -> None:
        """Отправка в центральный чат. Альбом отправляется один раз на всю медиа-группу."""
        if message.media_group_id:
            group_id = str(message.media_group_id)

            if await poller_state.is_group_sent(message.chat.id, group_id):
                logger.info(f"Альбом {group_id} чата {message.chat.id} уже отправлен, пропускаем")
                return

            await poller_state.mark_group_sent(message.chat.id, group_id)
            await BotManager.send_media_group_from_userbot(
                chat_id,
                client,
                message.chat.id,
                group_id,
                processed_text,
            )
            return

        if getattr(message, "photo", None):
            await BotManager.send_photo_from_userbot(chat_id, client, message, processed_text)
            return

        await BotManager.send_message(chat_id, processed_text)
```

- [ ] **Step 3: Заменить отправку в ветке привязанного канала**

Найти блок (он идёт сразу после `add_userbot_source_link` и проверки стоп-слов,
перед `return`) и заменить его целиком:

```python
                if message.media_group_id:
                    await BotManager.send_media_group_from_userbot(
                        monitoring_chat_central_id,
                        client,
                        message.chat.id,
                        str(message.media_group_id),
                        processed_text
                    )
                elif message.photo:
                    await BotManager.send_photo_from_userbot(monitoring_chat_central_id, client, message, processed_text)
                else:
                    await BotManager.send_message(monitoring_chat_central_id, processed_text)
                return
```

на:

```python
                await Handlers._send_to_central(monitoring_chat_central_id, client, message, processed_text)
                return
```

- [ ] **Step 4: Заменить отправку в ветке непривязанного канала**

Найти блок в конце цикла `for central_chat_id, chat_keywords in target_central_chats.items():`
и заменить его целиком:

```python
                if message.media_group_id:
                    await BotManager.send_media_group_from_userbot(
                        central_chat_id,
                        client,
                        message.chat.id,
                        str(message.media_group_id),
                        processed_text
                    )
                elif message.photo:
                    await BotManager.send_photo_from_userbot(central_chat_id, client, message, processed_text)
                else:
                    await BotManager.send_message(central_chat_id, processed_text)
```

на:

```python
                await Handlers._send_to_central(central_chat_id, client, message, processed_text)
```

- [ ] **Step 5: Добавить отметку обработанного сообщения**

В `message_handler` сразу после строки:

```python
            logger.info(f"Чат {message.chat.id} ({candidate.title}) найден в базе данных")
```

вставить:

```python
            if await poller_state.is_seen(message.chat.id, message.id):
                logger.info(f"[{instance_id}] Сообщение {message_key} уже обработано ранее, пропускаем")
                return

            await poller_state.mark_seen(message.chat.id, message.id)
```

Отметка ставится после проверки чата в БД — так ключи создаются только для
мониторинг-каналов, а не для всех чатов аккаунта (юзербот видит весь входящий поток,
это тысячи сообщений в сутки).

- [ ] **Step 6: Проверить синтаксис изменённого модуля**

Run: `python -m py_compile app/userbot/handlers.py`
Expected: без вывода, код возврата 0

- [ ] **Step 7: Убедиться, что прежние блоки отправки не остались**

Run: `grep -c "send_media_group_from_userbot" app/userbot/handlers.py`
Expected: `1` — единственное упоминание внутри `_send_to_central`

- [ ] **Step 8: Прогнать весь набор тестов**

Run: `python -m pytest tests -v`
Expected: PASS, 15 passed

- [ ] **Step 9: Коммит**

```bash
git add app/userbot/handlers.py
git commit -m "Обработчик: отметки обработанных сообщений и однократная отправка альбомов"
```

---

### Task 5: Запуск поллера в процессе бота

**Files:**
- Modify: `app/__main__.py`

**Interfaces:**
- Consumes: `channel_poller` из Task 3

- [ ] **Step 1: Добавить поллер в запуск**

В `app/__main__.py` в ветке `elif os.environ["APP_CLIENT"] == "bot":` заменить блок:

```python
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
```

на:

```python
            from app.bot import run_bot
            from app.userbot.userbot_manager import userbot_manager
            from app.userbot.poller import channel_poller

            # Запускаем планировщик очистки для бота
            await cleanup_scheduler.start()

            await asyncio.gather(
                *[
                    userbot_manager.start(),
                    run_bot(),
                    channel_poller.start(),
                ],
            )
```

- [ ] **Step 2: Проверить синтаксис**

Run: `python -m py_compile app/__main__.py app/userbot/poller.py app/userbot/poller_state.py app/settings.py`
Expected: без вывода, код возврата 0

- [ ] **Step 3: Прогнать весь набор тестов**

Run: `python -m pytest tests -v`
Expected: PASS, 15 passed

- [ ] **Step 4: Коммит**

```bash
git add app/__main__.py
git commit -m "Запускаем поллер вместе с ботом и юзерботом"
```

---

## Проверка на проде (выполняет человек, не субагент)

После выката и перезапуска процесса `bot`:

1. **Bootstrap прошёл, старые посты не разосланы.** В первые минуты в логе есть строки
   «первая инициализация, стартовая позиция N» по каждому каналу, отправок нет:

   ```bash
   grep -c "первая инициализация" bot.log
   grep -c "Отправляем сообщение в чат" bot.log
   ```

2. **Молчавшие каналы дошли до обработчика** (через один-два интервала, ~5-10 минут):

   ```bash
   grep -c "chat_id=-1001297561296" bot.log   # Gorilla Crypto
   grep -c "chat_id=-1001727857237" bot.log   # Crypto Musk
   ```

3. **Дублей нет.** Посты живых каналов (MACD, `-1001390831351`) не задваиваются в
   центральных чатах — проверить глазами в Telegram.

4. **Рестарт не вызывает повторной рассылки.** Перезапустить процесс `bot`, убедиться,
   что в центральные чаты не улетели уже отправленные посты.

5. **Флуд-лимиты не срабатывают:**

   ```bash
   grep -c "FloodWait" bot.log
   ```

Если пункт 1 не выполняется и в чаты полетели старые посты — немедленно остановить
процесс и выставить `"poller_enabled": false` в `settings.json`.
