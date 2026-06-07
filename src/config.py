'''
Модуль конфигурации приложения. Загружает настройки из .env файла и предоставляет их через класс Settings.
'''

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    
    TELEGRAM_BOT_TOKEN: str
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    ENCRYPTION_KEY: str | None = None

settings = Settings()