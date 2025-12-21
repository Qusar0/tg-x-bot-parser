import asyncio
from loguru import logger
from app.database.redis import redis_store
from app.helpers import cleanup_old_redis_data


class CleanupScheduler:
    """Планировщик для периодической очистки старых данных"""
    
    def __init__(self, cleanup_interval_minutes: int = 30, memory_check_interval_minutes: int = 5):
        self.cleanup_interval = cleanup_interval_minutes * 60  # в секундах
        self.memory_check_interval = memory_check_interval_minutes * 60  # в секундах
        self.is_running = False
        self.cleanup_task = None
        self.memory_task = None
        self.max_memory_mb = 100  # Максимальное использование памяти в МБ
    
    async def start(self):
        """Запускает планировщик очистки"""
        if self.is_running:
            logger.warning("[CLEANUP_SCHEDULER] Планировщик уже запущен")
            return
        
        self.is_running = True
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        self.memory_task = asyncio.create_task(self._memory_monitor_loop())
        logger.info(f"[CLEANUP_SCHEDULER] Планировщик запущен:")
        logger.info(f"[CLEANUP_SCHEDULER] - Очистка каждые {self.cleanup_interval // 60} минут")
        logger.info(f"[CLEANUP_SCHEDULER] - Проверка памяти каждые {self.memory_check_interval // 60} минут")
    
    async def stop(self):
        """Останавливает планировщик очистки"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Останавливаем обе задачи
        tasks_to_cancel = [self.cleanup_task, self.memory_task]
        for task in tasks_to_cancel:
            if task:
                task.cancel()
        
        # Ждем завершения всех задач
        for task in tasks_to_cancel:
            if task:
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("[CLEANUP_SCHEDULER] Планировщик остановлен")
    
    async def _cleanup_loop(self):
        """Основной цикл очистки"""
        while self.is_running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                if self.is_running:  # Проверяем, что не остановились во время сна
                    await self._perform_cleanup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[CLEANUP_SCHEDULER] Ошибка в цикле очистки: {e}")
                # Продолжаем работу даже при ошибке
                await asyncio.sleep(60)  # Ждем минуту перед следующей попыткой
    
    async def _memory_monitor_loop(self):
        """Цикл мониторинга памяти"""
        while self.is_running:
            try:
                await asyncio.sleep(self.memory_check_interval)
                if self.is_running:
                    await self._check_memory_usage()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[MEMORY_MONITOR] Ошибка в мониторинге памяти: {e}")
                await asyncio.sleep(60)
    
    async def _perform_cleanup(self):
        """Выполняет очистку данных"""
        try:
            logger.info("[CLEANUP_SCHEDULER] Начинаем периодическую очистку...")
            
            # Очищаем старые данные из Redis
            deleted_posts = await cleanup_old_redis_data()
            
            # Получаем информацию о памяти
            memory_info = await redis_store.get_memory_usage()
            
            # Выполняем оптимизацию памяти Redis
            await redis_store.optimize_memory()
            
            logger.info(f"[CLEANUP_SCHEDULER] Очистка завершена:")
            logger.info(f"[CLEANUP_SCHEDULER] - Удалено постов: {deleted_posts}")
            logger.info(f"[CLEANUP_SCHEDULER] - Использовано памяти: {memory_info.get('used_memory_human', 'N/A')}")
            logger.info(f"[CLEANUP_SCHEDULER] - Количество ключей: {memory_info.get('keys_count', 'N/A')}")
            
        except Exception as e:
            logger.error(f"[CLEANUP_SCHEDULER] Ошибка при выполнении очистки: {e}")
    
    async def _check_memory_usage(self):
        """Проверяет использование памяти и при необходимости запускает очистку"""
        try:
            memory_info = await redis_store.get_memory_usage()
            used_memory_mb = memory_info.get('used_memory', 0) / (1024 * 1024)
            keys_count = memory_info.get('keys_count', 0)
            
            logger.info(f"[MEMORY_MONITOR] Использование памяти: {used_memory_mb:.2f} МБ, ключей: {keys_count}")
            
            # Если память превышает лимит, запускаем экстренную очистку
            if used_memory_mb > self.max_memory_mb:
                logger.warning(f"[MEMORY_MONITOR] Превышен лимит памяти! {used_memory_mb:.2f} МБ > {self.max_memory_mb} МБ")
                await self._emergency_cleanup()
                
        except Exception as e:
            logger.error(f"[MEMORY_MONITOR] Ошибка при проверке памяти: {e}")
    
    async def _emergency_cleanup(self):
        """Экстренная очистка при превышении лимитов памяти"""
        try:
            logger.warning("[EMERGENCY_CLEANUP] Запускаем экстренную очистку...")
            
            # Очищаем старые посты (старше 2 часов)
            deleted_posts = await redis_store.cleanup_old_posts(max_age_hours=2)
            
            logger.warning(f"[EMERGENCY_CLEANUP] Экстренная очистка завершена, удалено постов: {deleted_posts}")
            
        except Exception as e:
            logger.error(f"[EMERGENCY_CLEANUP] Ошибка при экстренной очистке: {e}")
    
    async def force_cleanup(self):
        """Принудительно выполняет очистку"""
        logger.info("[CLEANUP_SCHEDULER] Выполняем принудительную очистку...")
        await self._perform_cleanup()


# Глобальный экземпляр планировщика
# Настройки можно изменить здесь или добавить в конфиг
cleanup_scheduler = CleanupScheduler(
    cleanup_interval_minutes=1440,  # Очистка каждые 30 минут
    memory_check_interval_minutes=5  # Проверка памяти каждые 5 минут
)
