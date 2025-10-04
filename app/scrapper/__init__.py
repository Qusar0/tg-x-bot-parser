import asyncio
import json
import traceback
import random
from loguru import logger
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException
from app.database.repo.Word import WordRepo
from app.enums import WordType
from app.settings import settings
from app.bot.Manager import BotManager
from app.database.models.Word import Word
from app.helpers import preprocess_text, is_word_match, is_duplicate, get_fetched_post_ids, add_source_link
from app.queue import queue

with open("cookies.txt") as file:
    COOKIE_JSON = file.read().rstrip()


class Scrapper:
    def __init__(self):
        self.SEARCH_URL = "https://tgstat.ru/search"

        self.driver = None
        self.wait = None

        self.is_load_cookie = False

    def _load_driver(self):
        # options = uc.ChromeOptions()
        self.driver = uc.Chrome(
            use_subprocess=False,
            # options=options,
            driver_executable_path=ChromeDriverManager().install(),
        )
        self.wait = WebDriverWait(self.driver, 10)

    def _load_cookie(self):
        self.is_load_cookie = True
        data = json.loads(COOKIE_JSON)
        for cookie in data:
            self.driver.add_cookie({k: cookie[k] for k in {"name", "value"}})

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
                    await self.load_more_posts()
                except ElementNotInteractableException:
                    logger.warning('На странице не найдено больше записей.')
                    continue
                except Exception as ex:
                    logger.error(f'Ошибка при обработке записей {ex}')
                    continue
                finally:
                    logger.info(f"Ключевое слово '{keyword.title}' привязано к чату {keyword.central_chat_id}")
                    await self.parse_posts(keyword.central_chat_id, stopwords, keyword)
                    await asyncio.sleep(10)
        except Exception as ex:
            logger.error(ex)
            traceback.print_exc()

    async def parse_posts(self, chat_id: int, stopwords: list[Word], keyword: Word):
        FETCHED_CARDS = await get_fetched_post_ids()

        logger.info(f"Парсим и анализируем посты для чата {chat_id}")

        soup = BeautifulSoup(self.driver.page_source, "html.parser")

        cards = soup.select(".posts-list > .card")

        for card in cards:
            try:
                post_el = card.select_one(".post-text")
                if not post_el:
                    logger.debug("Пропускаем карточку: нет .post-text")
                    continue

                text = post_el.decode_contents(formatter="html")

                single_img = card.select_one(".post-img-img")
                carousel_img = card.select(".carousel-item .post-img-img")
                imgs = [img.get("src") for img in carousel_img if img.get("src")]
                card_header = card.select_one(".post-header .media-body a")

                id_el = card.select_one('[data-original-title="Постоянная ссылка на публикацию"]')
                id = id_el.get("data-src") if id_el else None
                if not id:
                    logger.debug("Пропускаем карточку: нет permalink id")
                    continue

                if id in FETCHED_CARDS:
                    continue

                FETCHED_CARDS.append(id)

                if is_word_match(text, stopwords):
                    logger.info(f"Нашли стоп-слова в сообщении: {id}")
                    continue

                if await is_duplicate(id, text):
                    logger.info(f"Сообщение дубликат: {id}")
                    continue

                processed_text = await preprocess_text(text, keyword)
                if card_header:
                    processed_text = await add_source_link(processed_text, card_header)

                if carousel_img:
                    logger.info(f"Добавляем в очередь: send_media_group в чат {chat_id}")
                    asyncio.create_task(queue.call((BotManager.send_media_group, chat_id, imgs, processed_text)))
                elif single_img:
                    single_img = single_img.get("src")
                    logger.info(f"Добавляем в очередь: send_photo в чат {chat_id}")
                    asyncio.create_task(queue.call((BotManager.send_photo, chat_id, single_img, processed_text)))
                else:
                    logger.info(f"Добавляем в очередь: send_message в чат {chat_id}")
                    asyncio.create_task(queue.call((BotManager.send_message, chat_id, processed_text)))
            except Exception as ex:
                logger.warning(f"Ошибка обработки карточки: {ex}")
                continue

    async def load_search_page(self):
        """Грузим поисковую страницу"""
        logger.info("Грузим поисковую страницу")

        self.driver.get(self.SEARCH_URL)
        if not self.is_load_cookie:
            self._load_cookie()
            self.driver.refresh()

        await asyncio.sleep(1)

    async def input_search_keywords(self, keyword_request: str, is_first_search: bool):
        """Вводим поисковой запрос"""
        if is_first_search:
            search_input = self.driver.find_element(By.XPATH, '//*[@id="search-form-top"]/div/div/input')
        else:
            search_input = self.driver.find_element(By.XPATH, '//*[@id="q"]')
            search_input.clear()

        search_input.send_keys(keyword_request)
        await asyncio.sleep(1)
        search_input.send_keys(Keys.RETURN)

        logger.debug(f"Делаем запрос с ключами: {keyword_request}")

    async def load_more_posts(self):
        """Нажимаем кнопку загрузить еще"""
        logger.info("Открываем больше постов")
        try:
            button = self.driver.find_element(By.XPATH, '//*[@id="sticky-center-column"]/div[3]/div[2]/button')
            click_count = settings.get_scrapper_more_posts_clicks_count()

            for _ in range(click_count):
                button.click()
                await asyncio.sleep(2)

        except NoSuchElementException:
            logger.warning("Не нашли кнопки для загрузки дополнительных постов")

    async def start(self):
        self._load_driver()

        load_count = 0
        try:
            while True:
                load_count += 1
                logger.info(f"Начинаем проверку №{load_count}")
                await self.fetch_url()

                sleep_sec = settings.get_scrapper_page_sleep_sec()
                sleep_sec = random.randint(sleep_sec, sleep_sec + 60)
                logger.info(f"Спим: {sleep_sec} сек.")
                await asyncio.sleep(sleep_sec)
        finally:
            self.driver.close()
            self.driver.quit()


scrapper = Scrapper()
