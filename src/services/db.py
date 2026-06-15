import logging
import os
from sqlite3 import Connection, connect
from pathlib import Path
from cryptography.fernet import Fernet
from src.config import settings

# Инициализация логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройка шифрования
cipher_suite = Fernet(settings.ENCRYPTION_KEY.encode()) if settings.ENCRYPTION_KEY else None

def encrypt_data(data: str) -> str:
    """Шифрует строку, если задан ключ"""
    if not cipher_suite:
        return data
    return cipher_suite.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    """Дешифрует строку, если задан ключ"""
    if not cipher_suite:
        return encrypted_data
    try:
        return cipher_suite.decrypt(encrypted_data.encode()).decode()
    except Exception:
        # Если данные не зашифрованы или ключ неверный, возвращаем как есть
        return encrypted_data

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
    encrypted_token = encrypt_data(google_token)
    conn = await get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO users (telegram_id, username, google_token)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                google_token = excluded.google_token
        """, (telegram_id, username, encrypted_token))
        conn.commit()
        logger.info(f"Пользователь {telegram_id} сохранен/обновлен.")
    except Exception as e:
        logger.error(f"Ошибка при сохранении пользователя: {e}")
    finally:
        conn.close()

async def update_user_token(telegram_id: int, google_token: str) -> None:
    """
    Обновление только Google токена пользователя
    
    Args:
        telegram_id: ID пользователя в Telegram
        google_token: JSON строка с токенами Google
    """
    encrypted_token = encrypt_data(google_token)
    conn = await get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE users SET google_token = ? WHERE telegram_id = ?
        """, (encrypted_token, telegram_id))
        conn.commit()
        logger.info(f"Токен пользователя {telegram_id} обновлен.")
    except Exception as e:
        logger.error(f"Ошибка при обновлении токена пользователя {telegram_id}: {e}")
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
        if result and result[0]:
            return decrypt_data(result[0])
        return None
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

async def get_all_reminders() -> list[tuple[int, int]]:
    """
    Получение списка всех пользователей с настройками напоминаний.
    Returns: список кортежей (telegram_id, reminder_time_minutes)
    """
    conn = await get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT telegram_id, reminder_time FROM reminder")
        return cursor.fetchall()
    except Exception as e:
        logger.error(f"Ошибка при получении всех напоминаний: {e}")
        return []
    finally:
        conn.close()