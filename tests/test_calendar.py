import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Эта переменная определяет, что именно мы можем делать с календарем.
# В данном случае - полный доступ (чтение, создание, удаление событий).
SCOPES = ['https://www.googleapis.com/auth/calendar']

def main():
    creds = None
    
    # 1. Проверяем, есть ли уже сохраненный токен от предыдущих успешных авторизаций
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
    # 2. Если токена нет или он недействителен, запускаем процесс авторизации
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Если токен просто просрочился, обновляем его
            creds.refresh(Request())
        else:
            # Если токена вообще нет, открываем браузер для входа
            print("Токен не найден или устарел. Открываем браузер для авторизации...")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            
            # Запускаем локальный сервер на порту 3000
            #  http://localhost:3000/ должен быть добавлен в Google Console
            creds = flow.run_local_server(port=3000)
            
        # 3. Сохраняем полученный токен в файл, чтобы не логиниться каждый раз
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            print("Успех! Файл token.json успешно создан и сохранен.")

    # 4. Проверка доступа: пробуем получить события из календаря
    try:
        # Подключаемся к сервису Google Calendar API (версия 3)
        service = build('calendar', 'v3', credentials=creds)

        # Получаем текущее время в формате UTC
        now = datetime.datetime.utcnow().isoformat() + 'Z' 
        
        print('\nПодключение к API успешно! Получаем 5 ближайших событий...')
        # Запрашиваем события из основного календаря ('primary')
        events_result = service.events().list(
            calendarId='primary', 
            timeMin=now,
            maxResults=5, 
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])

        if not events:
            print('В вашем календаре пока нет предстоящих событий.')
            return

        # Выводим найденные события на экран
        print("\n--- ВАШИ БЛИЖАЙШИЕ СОБЫТИЯ ---")
        for event in events:
            # Дата события (может быть точным временем или просто датой, если событие на весь день)
            start = event['start'].get('dateTime', event['start'].get('date'))
            
            # Преобразуем немного формат времени для красоты (отрезаем лишнее)
            start_formatted = start.replace('T', ' ')[:16] 
            
            # Название события
            summary = event.get('summary', '(Без названия)')
            
            print(f"📅 {start_formatted} -> {summary}")

    except HttpError as error:
        print(f'\n[ОШИБКА] Произошла ошибка при обращении к Google API: {error}')

if __name__ == '__main__':
    main()