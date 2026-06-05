import logging
import os
from sqlite3 import Connection, connect
from pathlib import Path

# Инициализация логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Путь к БД относительно корня проекта
BASE_DIR = Path(__file__).parent.parent.parent
DB_PATH = BASE_DIR / "src" / "data" / "database.db"

async def get_db_connection() -> Connection:
    """Получение подключения к базе данных SQLite"""
    # Создаем директорию если её нет
    os.makedirs(DB_PATH.parent, exist_ok=True)
    conn = connect(str(DB_PATH))
    return conn


async def init_db() -> None:
    """Инициализация базы данных и создание таблиц"""
    conn = await get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Создание таблицы users если её нет
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                google_token TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        logger.info("Таблица users создана/проверена успешно")
    except Exception as e:
        logger.error(f"Ошибка при создании таблицы users: {e}")
    
    try:
        # Создание таблицы reminder если её нет
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminder (
                id INTEGER PRIMARY KEY,
                telegram_id INTEGER UNIQUE NOT NULL,
                reminder_time INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        logger.info("Таблица reminder создана/проверена успешно")
    except Exception as e:
        logger.error(f"Ошибка при создании таблицы reminder: {e}")

    finally:
        conn.close()

async def user_exists(telegram_id: int) -> bool:
    """
    Проверка наличия пользователя в таблице users по telegram_id
    
    Args:
        telegram_id: ID пользователя в Telegram
    
    Returns:
        True если пользователь найден, False иначе
    """
    conn = await get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT 1 FROM users WHERE telegram_id = ?", (telegram_id,))
        result = cursor.fetchone()
        return result is not None
    except Exception as e:
        logger.error(f"Ошибка при проверке наличия пользователя: {e}")
        return False
    finally:
        conn.close()

async def save_user(telegram_id: int, username: str, google_token: str) -> None:
    """
    Сохранение или обновление пользователя и его токена
    
    Args:
        telegram_id: ID пользователя в Telegram
        username: Имя пользователя
        google_token: JSON строка с токенами Google
    """
    conn = await get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO users (telegram_id, username, google_token)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                google_token = excluded.google_token
        """, (telegram_id, username, google_token))
        conn.commit()
        logger.info(f"Пользователь {telegram_id} сохранен/обновлен.")
    except Exception as e:
        logger.error(f"Ошибка при сохранении пользователя: {e}")
    finally:
        conn.close()

async def get_user_token(telegram_id: int) -> str | None:
    """
    Получение Google токена пользователя по telegram_id
    
    Args:
        telegram_id: ID пользователя в Telegram
        
    Returns:
        JSON строка с токеном или None
    """
    conn = await get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT google_token FROM users WHERE telegram_id = ?", (telegram_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        logger.error(f"Ошибка при получении токена пользователя {telegram_id}: {e}")
        return None
    finally:
        conn.close()

async def save_reminder(telegram_id: int, reminder_time: int) -> None:
    """
    Сохранение или обновление напоминания для пользователя
    
    Args:
        telegram_id: ID пользователя в Telegram
        reminder_time: Время напоминания в секундах до события
    """
    conn = await get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO reminder (telegram_id, reminder_time)
            VALUES (?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                reminder_time = excluded.reminder_time
        """, (telegram_id, reminder_time))
        conn.commit()
        logger.info(f"Напоминание для пользователя {telegram_id} сохранено/обновлено.")
    except Exception as e:
        logger.error(f"Ошибка при сохранении напоминания для пользователя {telegram_id}: {e}")
    finally:
        conn.close()

async def get_reminder(telegram_id: int) -> int | None:
    """
    Получение времени напоминания для пользователя по telegram_id
    
    Args:
        telegram_id: ID пользователя в Telegram
        
    Returns:
        Время напоминания в секундах до события или None
    """
    conn = await get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT reminder_time FROM reminder WHERE telegram_id = ?", (telegram_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        logger.error(f"Ошибка при получении напоминания для пользователя {telegram_id}: {e}")
        return None
    finally:
        conn.close()