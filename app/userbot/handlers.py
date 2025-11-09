from loguru import logger
from pyrogram import Client, types
from pyrogram.errors import PeerIdInvalid
from app.database.repo.Chat import ChatRepo
from app.userbot.filters.is_word_match import is_word_match
from app.enums import WordType
from app.bot.Manager import BotManager
from app.helpers import is_duplicate, preprocess_text, add_userbot_source_link


class Handlers:
    # Кэш для отслеживания обработанных сообщений в рамках сессии
    _processed_messages = set()
    _instance_id = None
    _max_cache_size = 5000  # Уменьшаем максимальный размер кэша
    
    @classmethod
    def get_instance_id(cls):
        if cls._instance_id is None:
            import uuid
            cls._instance_id = str(uuid.uuid4())[:8]
        return cls._instance_id
    
    @staticmethod
    async def message_handler(client: Client, message: types.Message):
        try:
            instance_id = Handlers.get_instance_id()
            logger.info(f"[{instance_id}] Получено сообщение от userbot: chat_id={message.chat.id}, message_id={message.id}, date={message.date}, text_length={len(message.text or message.caption or '')}")
            logger.info(f"[{instance_id}] Полный текст сообщения: {message.text or message.caption or ''}")
            
            if message.service:
                logger.info("Сообщение является служебным, пропускаем")
                return

            text = message.text or message.caption

            if not text:
                logger.info("Сообщение не содержит текста, пропускаем")
                return
            
            message_key = f"{message.chat.id}:{message.id}"
            if message_key in Handlers._processed_messages:
                logger.warning(f"[{instance_id}] ДУБЛИКАТ! Сообщение уже обработано: {message.link}")
                return
            
            logger.info(f"[{instance_id}] Добавляем сообщение в кэш: {message_key}")
            Handlers._processed_messages.add(message_key)
            
            # Более частое и эффективное очищение кэша
            if len(Handlers._processed_messages) > Handlers._max_cache_size:
                logger.info(f"[{instance_id}] Очищаем старые записи из кэша (было: {len(Handlers._processed_messages)})")
                # Оставляем только половину от максимального размера
                keep_size = Handlers._max_cache_size // 2
                Handlers._processed_messages = set(list(Handlers._processed_messages)[-keep_size:])
                logger.info(f"[{instance_id}] Кэш очищен, осталось: {len(Handlers._processed_messages)} записей")

            candidate = await ChatRepo.get_by_telegram_id(message.chat.id)
            if not candidate:
                logger.info(f"Чат {message.chat.id} не найден в базе данных для мониторинга")
                return

            if candidate.is_central:
                logger.info(f"Пропускаем сообщение из центрального чата {message.chat.id} ({candidate.title})")
                return

            logger.info(f"Чат {message.chat.id} ({candidate.title}) найден в базе данных")

            keywords = await is_word_match(text, WordType.tg_keyword)
            if not keywords:
                logger.info(f"В тексте не найдено ключевых слов: {text[:100]}...")
                return

            logger.info(f"Найдено {len(keywords)} ключевых слов: {[kw.title for kw in keywords]}")

            stopwords = await is_word_match(text, WordType.tg_stopword)
            if stopwords:
                logger.info(f"Найдены стоп-слова, пропускаем сообщение: {[sw.title for sw in stopwords]}")
                return

            if await is_duplicate(f"{message.chat.id}:{message.id}", text):
                logger.info(f"Поймали дубликат в сообщении: {message.link}")
                return

            logger.info(f"Получили сообщение: {message.link}")

            central_chats = {}
            for keyword in keywords:
                if keyword.central_chat_id not in central_chats:
                    central_chats[keyword.central_chat_id] = []
                central_chats[keyword.central_chat_id].append(keyword)
            
            logger.info(f"Найдено {len(central_chats)} центральных чатов для отправки")
            # Получить из бд central_chat_id по monitoring_chats(message.chat.id))
            central_chat_for_monitoring = await ChatRepo.get_central_chats_by_monitoring(message.chat.id)
            
            for central_chat_id, chat_keywords in central_chats.items():
                # Если central_chat_monitoring заполнено в бд
                if central_chat_for_monitoring:
                    # Сравнить central_chat_id с central_chat_id_monitoring
                    if not await ChatRepo.is_id_contains(central_chat_id, central_chat_for_monitoring):
                        continue
                logger.info(f"Отправляем сообщение в центральный чат {central_chat_id} (найдено {len(chat_keywords)} ключевых слов)")
                keyword = chat_keywords[0]
                
                processed_text = await preprocess_text(
                    text.html,
                    keyword,
                    allowed_tags=["b", "i", "u", "s", "em", "code", "stroke", "br", "p"],
                    allowed_attrs={},
                    platform="tg"
                )

                processed_text = await add_userbot_source_link(
                    processed_text,
                    candidate.title,
                    candidate.link,
                    message.chat.id
                )

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
        except PeerIdInvalid as e:
            logger.warning(f"PeerIdInvalid error in message handler: {e}")
        except Exception as e:
            logger.error(f"Error in message handler: {e}")
