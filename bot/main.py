import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import settings
from bot.database.database import init_db
from bot.middlewares.role_middleware import RoleMiddleware
from bot.middlewares.logging_middleware import LoggingMiddleware
from bot.handlers import common_handlers, admin_handlers, manager_handlers, group_analysis_handlers
from bot.services.scheduler_service import SchedulerService

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/bot.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота"""
    # Создаём директории если их нет
    import os
    for directory in ["data", "logs", "exports"]:
        os.makedirs(directory, exist_ok=True)
    
    # Инициализация базы данных
    await init_db()
    logger.info("Database initialized")
    
    # Инициализация бота и диспетчера
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())
    
    # Регистрация middleware
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())
    dp.message.middleware(RoleMiddleware())
    dp.callback_query.middleware(RoleMiddleware())
    
    # Регистрация роутеров
    dp.include_router(common_handlers.router)
    dp.include_router(admin_handlers.router)
    dp.include_router(manager_handlers.router)
    dp.include_router(group_analysis_handlers.router)
    
    # Запуск планировщика
    scheduler = SchedulerService(bot)
    scheduler.start()
    
    try:
        logger.info("Bot starting...")
        # Включаем все необходимые типы обновлений, включая chat_member для отслеживания участников групп
        allowed_updates = list(dp.resolve_used_update_types())
        if "chat_member" not in allowed_updates:
            allowed_updates.append("chat_member")
        if "my_chat_member" not in allowed_updates:
            allowed_updates.append("my_chat_member")
        logger.info(f"Allowed updates: {allowed_updates}")
        await dp.start_polling(bot, allowed_updates=allowed_updates)
    finally:
        scheduler.shutdown()
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")

