import datetime
import json
import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError

from src.services.db import get_user_token, update_user_token

logger = logging.getLogger(__name__)

# Скоупы для доступа к календарю
SCOPES = ['https://www.googleapis.com/auth/calendar']

class TokenRevokedError(Exception):
    """Исключение, выбрасываемое когда токен был отозван или стал недействительным"""
    pass

async def get_calendar_service(telegram_id: int) -> build:
    """Создает и возвращает сервис Google Calendar для пользователя"""
    token_json = await get_user_token(telegram_id)
    if not token_json:
        return None
    
    try:
        creds_data = json.loads(token_json)
        creds = Credentials.from_authorized_user_info(creds_data, SCOPES)
        
        # Если токен просрочен, пробуем обновить
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Сохраняем обновленный токен обратно в БД
                await update_user_token(telegram_id, creds.to_json())
            except RefreshError as e:
                if 'invalid_grant' in str(e):
                    logger.warning(f"Токен пользователя {telegram_id} отозван или недействителен: {e}")
                    raise TokenRevokedError(f"Доступ отозван: {e}")
                raise e
            
        service = build('calendar', 'v3', credentials=creds)
        return service
    except TokenRevokedError:
        # Пробрасываем выше, чтобы обработчик бота мог отреагировать
        raise
    except Exception as e:
        logger.error(f"Ошибка при создании сервиса календаря: {e}")
        return None

async def get_upcoming_events(telegram_id: int, max_results: int = 5) -> list:
    """Получение ближайших событий из календаря пользователя"""
    service = await get_calendar_service(telegram_id)
    if not service:
        return None
        
    try:
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId='primary', 
            timeMin=now,
            maxResults=max_results, 
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        return events
    except HttpError as error:
        logger.error(f'Ошибка при получении событий: {error}')
        return []

async def get_past_events(telegram_id: int, max_results: int = 10):
    """Получение 10 последних прошедших событий пользователя"""
    service = await get_calendar_service(telegram_id)
    if not service:
        return None

    try:
        now_dt = datetime.datetime.utcnow()
        all_events = []
        
        time_min_dt = now_dt - datetime.timedelta(days=30)
        time_min = time_min_dt.isoformat() + 'Z'
        time_max = now_dt.isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary', 
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime',
            maxResults=250 
        ).execute()

        all_events = events_result.get('items', [])
        
        # Сортируем полученные события (от новых к старым) по времени НАЧАЛА
        sorted_events = sorted(
            all_events, 
            key=lambda x: x['start'].get('dateTime', x['start'].get('date')), 
            reverse=True
        )

        return sorted_events[:max_results]
    except HttpError as error:
        logger.error(f'Ошибка при получении истории: {error}')
        return []

def format_events(events, title="Ближайшие события"):
    """Форматирует список событий в красивую строку для Telegram"""
    if not events:
        return f"📅 {title} не найдены."

    res = f"📅 **{title}:**\n\n"
    for event in events:
        # Получаем начало и конец события
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))

        # Форматируем время
        try:
            if 'T' in start:
                # Событие с конкретным временем
                dt_start = datetime.datetime.fromisoformat(start.replace('Z', '+00:00'))
                dt_end = datetime.datetime.fromisoformat(end.replace('Z', '+00:00'))

                time_range = f"{dt_start.strftime('%d.%m %H:%M')}—{dt_end.strftime('%H:%M')}"
            else:
                # Событие на весь день
                time_range = f"{start} (весь день)"
        except Exception:
            # Фолбэк на случай ошибки парсинга
            time_range = f"{start[:16].replace('T', ' ')}"

        summary = event.get('summary', '(Без названия)')
        res += f"• `{time_range}` — **{summary}**\n"

    return res
