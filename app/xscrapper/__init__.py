import asyncio
import time
import json
import traceback
import random
from xml.sax import default_parser_list
from lxml import html
from loguru import logger
from datetime import datetime, timezone, timedelta

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.database.repo.Word import WordRepo
from app.enums import WordType
from app.settings import settings
from app.bot.Manager import BotManager
from app.database.models.Word import Word
from app.helpers import preprocess_text, is_word_match, is_duplicate, get_fetched_post_ids
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
        self.p = await async_playwright().start()
        self.browser = await self.p.chromium.launch(
            headless=False,
            # executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            # proxy={
            #     "server": "http://130.254.41.43:6663",
            #     "username": "user239081",
            #     "password": "6iogl9"
            # }
        )
        self.context = await self.browser.new_context(
        )

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
            keywords = await WordRepo.get_all(WordType.keyword)
            stopwords = await WordRepo.get_all(WordType.stopword)

            for idx, keyword in enumerate(keywords, start=1):
                try:
                    is_first_search = idx == 1

                    if is_first_search:
                        await self.load_search_page()

                    await self.input_search_keywords(keyword.title, is_first_search)

                    await self.parse_posts(keyword.central_chat_id, stopwords, keyword)
                    #self.load_more_posts()

                # except ElementNotInteractableException:
                #     logger.warning('На странице не найдено больше записей.')
                #     continue
                # except Exception as ex:
                #     logger.error(f'Ошибка при обработке записей {ex}')
                #     continue
                finally:
                    #
                    await asyncio.sleep(10)
        except Exception as ex:
            logger.error(ex)
            traceback.print_exc()

    async def parse_posts(self, chat_id: int, stopwords: list[Word], keyword: Word):
        FETCHED_CARDS = await get_fetched_post_ids()
        while True:
            exit_loop = False

            logger.info("Парсим и анализируем видимые посты")
            await self.page.wait_for_timeout(5000)
            html_content = await self.page.content()
            soup = BeautifulSoup(html_content, "lxml")

            cards = soup.select("article[data-testid='tweet']")
            print(len(cards))
            for card in cards:
                time_tag = card.find("time")
                if time_tag:
                    datetime_str = time_tag.get("datetime")
                    tweet_time = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))  # UTC
                    now = datetime.now(timezone.utc)

                    # Разница во времени
                    delta = now - tweet_time

                    # Проверяем, что не старше 24 часов
                    if delta > timedelta(days=1):
                        exit_loop = True  # ставим флаг выхода
                        break


                tweet_div = card.find('div', {'data-testid': 'tweetText'})
                if tweet_div:
                    tweet_text = tweet_div.get_text(separator=' ', strip=True)
                    print(tweet_text)

                photo_divs = card.find_all("div", {"data-testid": "tweetPhoto"})
                imgs = []
                for div in photo_divs:
                    img = div.find("img")  # ищем тег <img> внутри div
                    if img and img.get("src"):
                        imgs.append(img["src"])
                print(imgs)

                a_tag = card.find("a", href=lambda x: x and "/status/" in x)
                if a_tag:
                    id = a_tag.get("href").split('/')[-1]
                    print(id)
                if id in FETCHED_CARDS:
                    continue

                FETCHED_CARDS.append(id)

            if exit_loop:
                break

            await self.page.evaluate("""
                window.scrollBy(0, window.innerHeight);
            """)
            await self.page.wait_for_timeout(1000)

                # if id in FETCHED_CARDS:
                #     continue

                # FETCHED_CARDS.append(id)

                # if is_word_match(text, stopwords):
                #     logger.info(f"Нашли стоп-слова в сообщении: {id}")
                #     continue

                # if await is_duplicate(id, text):
                #     logger.info(f"Сообщение дубликат: {id}")
                #     return

                # processed_text = preprocess_text(text, keyword)

                # if carousel_img:
                #     asyncio.create_task(queue.call((BotManager.send_media_group, chat_id, imgs, processed_text)))
                # elif single_img:
                #     single_img = single_img.get("src")
                #     asyncio.create_task(queue.call((BotManager.send_photo, chat_id, single_img, processed_text)))
                # else:
                #     asyncio.create_task(queue.call((BotManager.send_message, chat_id, processed_text)))


    async def load_search_page(self):
        """Грузим поисковую страницу"""
        logger.info("Грузим поисковую страницу")
        self.page = await self.context.new_page()
        if not self.is_load_cookie:
            await self._load_cookie()
        await self.page.goto(self.SEARCH_URL)

        time.sleep(4)

    async def input_search_keywords(self, keyword_request: str, is_first_search: bool):
        """Вводим поисковой запрос"""

        input_selector = "input[placeholder='Search']"
        await self.page.wait_for_selector(input_selector)
        await self.page.fill(input_selector, keyword_request)
        time.sleep(1)
        await self.page.press(input_selector, "Enter")
        time.sleep(1)
        if is_first_search:
            latest_button = '//nav/div/div[2]/div/div[2]/a'
            await self.page.locator(latest_button).click()

        logger.debug(f"Делаем запрос с ключами: {keyword_request}")

    # def load_more_posts(self):
    #     """Нажимаем кнопку загрузить еще"""
    #     logger.info("Открываем больше постов")
    #     try:
    #         button = self.driver.find_element(By.XPATH, '//*[@id="sticky-center-column"]/div[3]/div[2]/button')
    #         click_count = settings.get_scrapper_more_posts_clicks_count()

    #         for _ in range(click_count):
    #             button.click()
    #             time.sleep(2)

    #     except NoSuchElementException:
    #         logger.warning("Не нашли кнопки для загрузки дополнительных постов")

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
                await self.page.wait_for_timeout(29999000)  # пауза 2 секунды (в миллисекундах)

        finally:
            await self.browser.close()
            await self.p.stop()


xscrapper = XScrapper()
