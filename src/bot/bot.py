from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio
import logging
import sys
from pathlib import Path

# Добавляем корневой каталог проекта в sys.path
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.config import settings
from src.bot import bot_handlers
from src.services.db import init_db
from src.services.scheduler import setup_scheduler, scheduler

# Инициализация логирования (базовая)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

storage = MemoryStorage()
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher(storage=storage)

# Подключение роутера с обработчиками
dp.include_router(bot_handlers.router)

async def main():
    """Главная функция бота"""
    # Инициализация БД
    await init_db()
    
    # Инициализация планировщика
    await setup_scheduler(bot)
    
    try:
        logger.info("Бот запущен")
        await dp.start_polling(bot)
    finally:
        if scheduler.running:
            scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
