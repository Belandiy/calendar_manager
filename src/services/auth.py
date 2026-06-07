import os
import logging
from google_auth_oauthlib.flow import Flow
from src.services.db import save_user
from src.config import settings
from src.services.db import save_reminder

# Разрешаем HTTP для разработки (Google OAuth требует HTTPS по умолчанию)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

logger = logging.getLogger(__name__)

def get_client_config():
    """Формирует конфигурацию клиента из настроек в памяти"""
    return {
        "installed": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        }
    }

async def get_google_auth_url() -> tuple[str, str]:
    """
    Генерирует ссылку для авторизации через Google OAuth 2.0.
    """
    flow = Flow.from_client_config(
        get_client_config(),
        scopes=['https://www.googleapis.com/auth/calendar'],
        redirect_uri='http://localhost' 
    )

    # Генерируем ссылку и сохраняем verifier для PKCE
    auth_url, _ = flow.authorization_url(prompt='consent')
    return auth_url, flow.code_verifier

async def process_auth_response(telegram_id: int, username: str, auth_response_url: str, code_verifier: str) -> bool:
    """
    Обменивает присланную пользователем ссылку на токены и сохраняет их в БД.
    """
    try:
        flow = Flow.from_client_config(
            get_client_config(),
            scopes=['https://www.googleapis.com/auth/calendar'],
            redirect_uri='http://localhost'
        )
        # Устанавливаем тот же verifier, который был при генерации ссылки
        flow.code_verifier = code_verifier
        
        flow.fetch_token(authorization_response=auth_response_url)
        creds = flow.credentials
        
        # Сохраняем токены в БД
        await save_user(telegram_id, username, creds.to_json())
        
        # Устанавливаем напоминание по умолчанию (30 минут)
        await save_reminder(telegram_id, 30)
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при обмене токена для пользователя {telegram_id}: {e}", exc_info=True)
        return False
