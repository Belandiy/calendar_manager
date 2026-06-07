from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Добавляем корневой каталог проекта в sys.path
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

# Настройка логирования
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Очищаем существующие обработчики
root_logger = logging.getLogger()
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

file_handler = RotatingFileHandler(
    LOGS_DIR / "app.log", 
    maxBytes=5*1024*1024, 
    backupCount=5, 
    encoding='utf-8'
)
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

logger = logging.getLogger(__name__)

from src.config import settings
from src.bot import bot_handlers
from src.services.db import init_db
from src.services.scheduler import setup_scheduler, scheduler

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
