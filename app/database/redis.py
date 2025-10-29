from redis import asyncio as aioredis
from loguru import logger
from app.config import config


class RedisStore:
    def __init__(self, redis_url: str = "", db: int = 2):
        self.redis_uri = redis_url
        self.db = db
        self.redis = None

    async def connect(self):
        try:
            self.redis = await aioredis.from_url(self.redis_uri, decode_responses=True, db=self.db)
        except Exception as e:
            logger.error(f"[REDIS_CONNECT]: {e}")

    async def disconnect(self):
        try:
            await self.redis.close()
        except Exception as e:
            logger.error(f"[REDIS_DISCONNECT]: {e}")

    async def set_value(self, key: str, value: str):
        try:
            await self.redis.set(key, value)
        except Exception as e:
            logger.error(f"[REDIS_SET_VALUE] '{key}' in Redis: {e}")

    async def set_value_ex(self, key: str, value: str, expire_sec: int):
        try:
            await self.redis.setex(key, expire_sec, value)
        except Exception as e:
            logger.error(f"[REDIS_SET_VALUE_EX] '{key}' in Redis: {e}")

    async def get_value(self, key: str):
        try:
            result = await self.redis.get(key)
            return result
        except Exception as e:
            logger.error(f"[REDIS_GET_VALUE] '{key}' from Redis: {e}")

    async def keys(self, pattern: str) -> list:
        try:
            result = await self.redis.keys(pattern)
            return result or []
        except Exception as e:
            logger.error(f"[REDIS_KEYS] from Redis: {e}")
            return []

    async def values(self, pattern: str) -> list:
        try:
            keys = await self.keys(pattern)
            if not keys:
                return []
            result = await self.redis.mget(keys)
            return result or []
        except Exception as e:
            logger.error(f"[REDIS_VALUES] from Redis: {e}")
            return []

    async def increment(self, key: str, amount: int = 1):
        try:
            result = await self.redis.incrby(key, amount)
            return result
        except Exception as e:
            logger.error(f"[REDIS_INCR] from Redis: {e}")

    async def delete_keys(self, pattern: str) -> int:
        """Удаляет ключи по паттерну и возвращает количество удаленных ключей"""
        try:
            keys = await self.keys(pattern)
            if not keys:
                return 0
            result = await self.redis.delete(*keys)
            logger.info(f"[REDIS_DELETE_KEYS] Удалено {result} ключей по паттерну: {pattern}")
            return result
        except Exception as e:
            logger.error(f"[REDIS_DELETE_KEYS] Ошибка удаления ключей: {e}")
            return 0

    async def cleanup_old_posts(self, max_age_hours: int = 2) -> int:
        """Очищает старые посты старше указанного количества часов"""
        try:
            # Получаем все ключи постов
            post_keys = await self.keys("post:*")
            if not post_keys:
                return 0
            
            # Получаем TTL для каждого ключа
            current_time = await self.redis.time()
            current_timestamp = int(current_time[0])
            max_age_seconds = max_age_hours * 3600
            
            keys_to_delete = []
            for key in post_keys:
                # Получаем время создания ключа через TTL
                ttl = await self.redis.ttl(key)
                if ttl > 0:
                    # Вычисляем время создания: current_time - (original_ttl - current_ttl)
                    # original_ttl = 24 * 3600 (24 часа)
                    original_ttl = 24 * 3600
                    created_time = current_timestamp - (original_ttl - ttl)
                    age_seconds = current_timestamp - created_time
                    
                    if age_seconds > max_age_seconds:
                        keys_to_delete.append(key)
            
            if keys_to_delete:
                deleted_count = await self.redis.delete(*keys_to_delete)
                logger.info(f"[REDIS_CLEANUP] Удалено {deleted_count} старых постов (старше {max_age_hours} часов)")
                return deleted_count
            else:
                logger.info(f"[REDIS_CLEANUP] Нет старых постов для удаления")
                return 0
                
        except Exception as e:
            logger.error(f"[REDIS_CLEANUP] Ошибка очистки старых постов: {e}")
            return 0

    async def get_memory_usage(self) -> dict:
        """Возвращает информацию об использовании памяти Redis"""
        try:
            info = await self.redis.info('memory')
            return {
                'used_memory': info.get('used_memory', 0),
                'used_memory_human': info.get('used_memory_human', '0B'),
                'maxmemory': info.get('maxmemory', 0),
                'maxmemory_human': info.get('maxmemory_human', '0B'),
                'keys_count': await self.redis.dbsize()
            }
        except Exception as e:
            logger.error(f"[REDIS_MEMORY_INFO] Ошибка получения информации о памяти: {e}")
            return {}
    
    async def optimize_memory(self):
        """Выполняет оптимизацию памяти Redis"""
        try:
            # Принудительно запускаем сборку мусора
            await self.redis.memory_purge()
            logger.info("[REDIS_OPTIMIZE] Выполнена оптимизация памяти Redis")
        except Exception as e:
            logger.error(f"[REDIS_OPTIMIZE] Ошибка оптимизации памяти: {e}")


redis_store = RedisStore(config.redis.uri)
