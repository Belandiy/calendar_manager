import datetime
import json
import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request

from src.services.db import get_user_token

logger = logging.getLogger(__name__)

# Скоупы для доступа к календарю
SCOPES = ['https://www.googleapis.com/auth/calendar']

async def get_calendar_service(telegram_id: int):
    """Создает и возвращает сервис Google Calendar для пользователя"""
    token_json = await get_user_token(telegram_id)
    if not token_json:
        return None
    
    try:
        creds_data = json.loads(token_json)
        creds = Credentials.from_authorized_user_info(creds_data, SCOPES)
        
        # Если токен просрочен, пробуем обновить
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Здесь в идеале нужно сохранить обновленный токен обратно в БД
            # Но для простоты пока оставим так
            
        service = build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Ошибка при создании сервиса календаря: {e}")
        return None

async def get_upcoming_events(telegram_id: int, max_results: int = 5):
    """Получение ближайших событий из календаря пользователя"""
    service = await get_calendar_service(telegram_id)
    if not service:
        return None
        
    try:
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' означает UTC время
        
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

def format_events(events):
    """Форматирует список событий в красивую строку для Telegram"""
    if not events:
        return "📅 У вас нет предстоящих событий."
        
    res = "📅 **Ваши ближайшие события:**\n\n"
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
                
                time_range = f"{dt_start.strftime('%d.%m %H:%M')} — {dt_end.strftime('%H:%M')}"
            else:
                # Событие на весь день
                time_range = f"{start} (весь день)"
        except Exception:
            # Фолбэк на случай ошибки парсинга
            time_range = f"{start[:16].replace('T', ' ')}"
            
        summary = event.get('summary', '(Без названия)')
        res += f"• `{time_range}` — **{summary}**\n"
        
    return res
