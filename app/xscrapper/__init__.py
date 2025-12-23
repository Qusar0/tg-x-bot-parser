import asyncio
import time
import json
import traceback
import random
from collections import defaultdict
from xml.sax import default_parser_list
from lxml import html
from loguru import logger
from datetime import datetime, timezone, timedelta

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.database.repo.Word import WordRepo
from app.database.repo.XChannel import XChannelRepo
from app.enums import WordType
from app.settings import settings
from app.bot.Manager import BotManager
from app.database.models.Word import Word
from app.helpers import (
    preprocess_text,
    is_duplicate,
    get_fetched_post_ids,
    add_x_link,
)
from app.userbot.filters.is_word_match import is_word_match
from app.queue import queue

with open("x_cookies.txt") as file:
    COOKIE_JSON = file.read().rstrip()


class XScrapper:
    def __init__(self):
        self.SEARCH_URL = "https://x.com/explore"

        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

        self.is_load_cookie = False

    async def _load_driver(self):
        # Исправляем проблему с child_watcher в Docker
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
        self.p = await async_playwright().start()
        
        # Настройки для Docker
        browser_args = [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--window-size=1920,1080'
        ]
        
        # Используем системный Chrome
        self.browser = await self.p.chromium.launch(
            headless=True,
            args=browser_args,
            proxy={
                "server": "http://130.254.41.43:6663",
                "username": "user239081",
                "password": "6iogl9"
            }
        )
        self.context = await self.browser.new_context()

    async def _load_cookie(self):
        self.is_load_cookie = True
        data_list = json.loads(COOKIE_JSON)
        cookies = []
        for data in data_list:
            cookie_instance = {}
            cookie_instance["name"] = data["name"]
            cookie_instance["url"] = f"https://{data['domain']}"
            cookie_instance["value"] = data["value"]
            cookie_instance["sameSite"] = "None"
            cookies.append(cookie_instance)
        await self.context.add_cookies(cookies)

    async def fetch_url(self):
        try:
            keywords = await WordRepo.get_all(WordType.x_keyword)
            stopwords = await WordRepo.get_all(WordType.x_stopword)
            min_rating = settings.get_x_channels_min_rating()
            channels_data = await XChannelRepo.get_by_rating_greater_than(min_rating - 1)
            
            if not keywords:
                logger.info("Ключевые слова отсутствуют.")
                await asyncio.sleep(10)
                return
            
            if not channels_data:
                logger.info(f"X каналы с рейтингом >= {min_rating} отсутствуют.")
                await asyncio.sleep(10)
                return

            # Группируем каналы по URL, чтобы поддерживать привязку одного X-канала к нескольким центральным чатам
            channels_by_url: dict[str, list] = defaultdict(list)
            for channel in channels_data:
                channels_by_url[channel.url].append(channel)

            channels = list(channels_by_url.keys())
            logger.info(f"Найдено {len(channels)} X каналов для мониторинга: {channels}")

            for idx, channel_url in enumerate(channels, start=1):
                try:
                    is_first_search = idx == 1

                    if is_first_search:
                        await self.load_search_page()

                    await self.load_search_channel(channel_url)
                    current_channels = channels_by_url[channel_url]
                    await self.parse_posts(stopwords, keywords, current_channels)

                finally:
                    await asyncio.sleep(10)

        except Exception as ex:
            logger.error(ex)
            traceback.print_exc()

    async def parse_posts(self, stopwords: list[Word], keywords: list[Word], current_channels: list = None):
        """Поиск постов, сбор информации по определенному чату"""
        current_channels = current_channels or []
        central_channels = [ch for ch in current_channels if ch.central_chat_id]
        chat_contexts = [ch.central_chat_id for ch in central_channels]
        fetched_by_chat = {cid: await get_fetched_post_ids(cid) for cid in chat_contexts}
        aggregated_fetched = set().union(*fetched_by_chat.values()) if fetched_by_chat else set()
        if fetched_by_chat:
            fetched_summary = {cid: len(ids) for cid, ids in fetched_by_chat.items()}
            logger.info(f"FETCHED_CARDS по чатам: {fetched_summary}")
        else:
            logger.info("FETCHED_CARDS: []")

        #  Страница грузится на профиль где не сразу видно посты, флаг нужен для первого скрола, когда ничего не нашло
        begin_page = True
        while True:
            exit_loop = False

            logger.info("Парсим и анализируем видимые посты")
            await self.page.wait_for_timeout(5000)
            html_content = await self.page.content()
            soup = BeautifulSoup(html_content, "lxml")

            cards = soup.select("article[data-testid='tweet']")
            ids = []
            for card in cards:
                a_tag = card.find("a", href=lambda x: x and "/status/" in x)
                if a_tag:
                    id = a_tag.get("href").split("/")[-1]
                    ids.append(id)
            logger.info(f"ids = {ids}")
            if aggregated_fetched and all(item in aggregated_fetched for item in ids) and not begin_page:
                logger.info("Закончились посты по этому ключ-слову")
                break
            if aggregated_fetched:
                logger.info(f"FETCHED_CARDS aggregated: {list(aggregated_fetched)}")
            for card in cards:
                # Парс идентификатора и ссылки
                a_tag = card.find("a", href=lambda x: x and "/status/" in x)
                if not a_tag:
                    logger.warning("Не найден идентификатор поста, пропускаем")
                    continue

                link = a_tag.get("href")
                id = link.split("/")[-1]
                logger.info(f"Tweet ID = {id}, Link = {link}")

                # Парс закрепа
                is_pinned = any(
                    "pinned" in div.get_text(strip=True).lower()
                    for div in card.find_all(["div", "span"])
                )

                if is_pinned:
                    logger.info("Найден закрепленный пост, пропускаем")
                    continue

                time_tag = card.find("time")
                if time_tag:
                    datetime_str = time_tag.get("datetime")
                    tweet_time = datetime.fromisoformat(
                        datetime_str.replace("Z", "+00:00")
                    )
                    now = datetime.now(timezone.utc)

                    delta = now - tweet_time

                    if delta > timedelta(days=1):
                        # Точка выхода, если возраст поста > 24h
                        exit_loop = True
                        break
                    logger.info(f"delta={delta}, exit_loop={exit_loop}")

                # Парс текста
                tweet_div = card.find("div", {"data-testid": "tweetText"})

                if tweet_div:
                    tweet_text = tweet_div.get_text(separator=" ", strip=True)
                    logger.info(f"Tweet text: {tweet_text[:100]}...")
                else:
                    tweet_text = ""
                    logger.warning("Не найден текст твита")

                tweet_div = str(tweet_div)

                photo_divs = card.find_all("div", {"data-testid": "tweetPhoto"})
                imgs = []
                for div in photo_divs:
                    img = div.find("img")
                    if img and img.get("src"):
                        imgs.append(img["src"])
                logger.info(f"{imgs}")

                matched_stopwords = await is_word_match(tweet_div, WordType.x_stopword)

                if central_channels:
                    for channel in central_channels:
                        chat_id = channel.central_chat_id
                        fetched_ids = fetched_by_chat.get(chat_id, [])
                        if id in fetched_ids:
                            logger.info(f"id: {id} already in FETCHED_CARDS for chat {chat_id}")
                            continue
                        fetched_ids.append(id)
                        fetched_by_chat[chat_id] = fetched_ids
                        aggregated_fetched.add(id)

                        if matched_stopwords:
                            logger.info(f"Нашли стоп-слова в сообщении: {id}")
                            continue

                        if await is_duplicate(id, tweet_text, chat_id=chat_id):
                            logger.info(f"Сообщение дубликат: {id} для чата {chat_id}")
                            continue
                        keyword = None
                        processed_text = await preprocess_text(tweet_div, keyword, platform="x")
                        channel_rating = channel.rating if channel else 0
                        channel_winrate = channel.winrate if channel else 0
                        processed_text = await add_x_link(processed_text, link, channel_rating, channel_winrate)
                        if len(imgs) > 1:
                            await queue.call(
                                (BotManager.send_media_group, chat_id, imgs, processed_text)
                            )

                        elif len(imgs) == 1:
                            await queue.call((BotManager.send_photo, chat_id, imgs[0], processed_text))
                        else:
                            await queue.call((BotManager.send_message, chat_id, processed_text))
                    # если канал привязан к центральным чатам, пропускаем дальнейшую обработку через ключевые слова
                    continue

                # СЛУЧАЙ 2: Ищем ключевые слова
                target_chats = set()  # Используем set для уникальности
                matched_keywords = []

                for keyword in keywords:
                    if keyword.title in tweet_div:
                        if keyword.central_chat_id:  # Проверяем, что у ключевого слова есть чат
                            target_chats.add(keyword.central_chat_id)
                            matched_keywords.append(keyword)  # Сохраняем для обработки

                # Если не нашли подходящих чатов - пропускаем
                if not target_chats:
                    continue

                # Проверяем стоп-слова и дубликаты (ОДИН РАЗ для поста)
                if matched_stopwords:
                    logger.info(f"Нашли стоп-слова в сообщении: {id}")
                    continue

                for chat_id in target_chats:
                    if await is_duplicate(id, tweet_text, chat_id=chat_id):
                        logger.info(f"Сообщение дубликат: {id} для чата {chat_id}")
                        continue
                    # Можно использовать первое подходящее ключевое слово или все
                    keyword_for_processing = matched_keywords[0] if matched_keywords else None
                    processed_text = await preprocess_text(tweet_div, keyword_for_processing, platform="x")
                    channel_rating = current_channel.rating if current_channel else 0
                    channel_winrate = current_channel.winrate if current_channel else 0
                    processed_text = await add_x_link(processed_text, link, channel_rating, channel_winrate)
                    if len(imgs) > 1:
                        await queue.call(
                            (BotManager.send_media_group, chat_id, imgs, processed_text)
                        )

                    elif len(imgs) == 1:
                        await queue.call((BotManager.send_photo, chat_id, imgs[0], processed_text))
                    else:
                        await queue.call((BotManager.send_message, chat_id, processed_text))

            if exit_loop:
                logger.info("Закончились посты в этом канале")
                break

            logger.info("Скролим страницу и ищем новые посты")
            await self.page.evaluate(
                """
                window.scrollBy(0, window.innerHeight);
            """
            )
            await self.page.wait_for_timeout(1000)
            begin_page = False

    async def load_search_page(self):
        """Грузим поисковую страницу"""
        logger.info("Грузим поисковую страницу")
        # Закрываем предыдущую страницу, если она существует, чтобы не накапливать страницы в памяти
        try:
            if self.page is not None:
                await self.page.close()
        except Exception:
            pass
        self.page = await self.context.new_page()
        if not self.is_load_cookie:
            await self._load_cookie()
        # Не блокируем событийный цикл
        await self.page.wait_for_timeout(2000)

    async def load_search_channel(self, channel_url: str):
        """Вводим поисковой запрос"""
        await self.page.goto(channel_url)
        await self.page.wait_for_timeout(1000)
        logger.debug(f"Начинаем поиск в канале: {channel_url}")

    async def start(self):
        await self._load_driver()

        load_count = 0
        try:
            while True:
                load_count += 1
                logger.info(f"Начинаем проверку №{load_count}")

                await self.fetch_url()

                sleep_sec = settings.get_scrapper_page_sleep_sec()
                sleep_sec = random.randint(sleep_sec, sleep_sec + 60)
                logger.info(f"Спим: {sleep_sec} сек.")


                if self.page is not None:
                    await self.page.wait_for_timeout(sleep_sec * 1000)
                else:
                    await asyncio.sleep(15)

        finally:
            try:
                if self.page is not None:
                    await self.page.close()
            except Exception:
                pass
            try:
                if self.context is not None:
                    await self.context.close()
            except Exception:
                pass
            try:
                if self.browser is not None:
                    await self.browser.close()
            except Exception:
                pass
            try:
                if self.p is not None:
                    await self.p.stop()
            except Exception:
                pass


xscrapper = XScrapper()
