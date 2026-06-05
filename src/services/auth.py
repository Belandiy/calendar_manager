import os
from google_auth_oauthlib.flow import Flow
from src.services.db import save_user

# Разрешаем HTTP для разработки (Google OAuth требует HTTPS по умолчанию)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

async def get_google_auth_url() -> tuple[str, str]:
    """
    Генерирует ссылку для авторизации через Google OAuth 2.0.
    
    Returns:
        tuple[str, str]: (URL для авторизации, code_verifier)
    """
    flow = Flow.from_client_secrets_file(
        'credentials.json',
        scopes=['https://www.googleapis.com/auth/calendar'],
        redirect_uri='http://localhost' 
    )

    # Генерируем ссылку и сохраняем verifier для PKCE
    auth_url, _ = flow.authorization_url(prompt='consent')
    return auth_url, flow.code_verifier

import logging

# Настройка логирования для этого модуля
logger = logging.getLogger(__name__)

async def process_auth_response(telegram_id: int, username: str, auth_response_url: str, code_verifier: str) -> bool:
    """
    Обменивает присланную пользователем ссылку на токены и сохраняет их в БД.
    
    Args:
        telegram_id: ID пользователя в Telegram
        username: Имя пользователя
        auth_response_url: Полный URL редиректа, присланный пользователем
        code_verifier: Верификатор кода (PKCE), сгенерированный на первом этапе
        
    Returns:
        bool: True если успешно, False иначе
    """
    try:
        flow = Flow.from_client_secrets_file(
            'credentials.json',
            scopes=['https://www.googleapis.com/auth/calendar'],
            redirect_uri='http://localhost'
        )
        # Устанавливаем тот же verifier, который был при генерации ссылки
        flow.code_verifier = code_verifier
        
        flow.fetch_token(authorization_response=auth_response_url)
        creds = flow.credentials
        
        # Сохраняем токены в БД
        await save_user(telegram_id, username, creds.to_json())
        return True
    except Exception as e:
        logger.error(f"Ошибка при обмене токена для пользователя {telegram_id}: {e}", exc_info=True)
        return False
