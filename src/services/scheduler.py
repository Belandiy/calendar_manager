import logging
import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

from src.services.db import get_all_reminders
from src.services.calendar import get_calendar_service, TokenRevokedError

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()

MONTHS_RU = (
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря"
)

async def setup_scheduler(bot: Bot):
    """Инициализация и запуск планировщика"""
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler запущен")
    
    # Добавляем периодическую проверку календарей
    # Используем строковое имя или отложенный импорт для избежания проблем,
    # но здесь функция в этом же файле, так что просто передаем ее.
    scheduler.add_job(
        check_calendars,
        "interval",
        minutes=5,
        args=[bot],
        id="check_calendars_sync",
        replace_existing=True
    )
    # Запускаем один раз сразу при старте (отложенно на 5 секунд, чтобы бот успел запуститься)
    scheduler.add_job(
        check_calendars, 
        "date", 
        run_date=datetime.datetime.now() + datetime.timedelta(seconds=5), 
        args=[bot],
        id="initial_check_sync",
        replace_existing=True
    )

async def send_reminder(bot: Bot, telegram_id: int, event_summary: str, event_time: str, event_link: str | None):
    """Отправка сообщения пользователю"""
    message = (
        f"⏰ **Напоминание!**\n\n"
        f"**Встреча:** \"{event_summary}\"\n"
        f"**Время:** {event_time}\n"
    )
    if event_link:
        message += f"**Ссылка:** [перейти]({event_link})"
    
    try:
        await bot.send_message(telegram_id, message, parse_mode="Markdown", disable_web_page_preview=False)
        logger.info(f"Напоминание отправлено пользователю {telegram_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке напоминания {telegram_id}: {e}")

async def check_calendars(bot: Bot):
    """Синхронизация локального расписания задач с Google Calendar"""
    logger.info("Запуск синхронизации календарей...")
    reminders = await get_all_reminders()
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Собираем все ID задач, которые должны быть в планировщике
    all_current_job_ids = set()
    
    for telegram_id, reminder_minutes in reminders:
        try:
            service = await get_calendar_service(telegram_id)
            if not service:
                continue
                
            # Ищем события на ближайшие 24 часа
            time_min = now.isoformat()
            time_max = (now + datetime.timedelta(days=1)).isoformat()
            
            events_result = service.events().list(
                calendarId='primary', 
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            for event in events:
                start_str = event['start'].get('dateTime', event['start'].get('date'))
                if not start_str: continue
                
                # Парсим время начала
                try:
                    start_dt = datetime.datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                except ValueError:
                    # Для событий на весь день формат может быть YYYY-MM-DD
                    start_dt = datetime.datetime.strptime(start_str, '%Y-%m-%d').replace(tzinfo=datetime.timezone.utc)
                
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=datetime.timezone.utc)
                
                # Вычисляем время триггера
                trigger_dt = start_dt - datetime.timedelta(minutes=int(reminder_minutes))
                
                # Если время напоминания еще не наступило (в будущем)
                if trigger_dt > now:
                    job_id = f"remind_{telegram_id}_{event['id']}"
                    all_current_job_ids.add(job_id)
                    
                    event_link = event.get('hangoutLink') or event.get('htmlLink')
                    
                    # Форматируем время для МСК (UTC+3)
                    msk_tz = datetime.timezone(datetime.timedelta(hours=3))
                    dt_msk = start_dt.astimezone(msk_tz)
                    
                    event_time_str = dt_msk.strftime(f'%d {MONTHS_RU[dt_msk.month]} %Y, %H:%M (МСК)')
                    
                    # Проверяем, нужно ли добавлять или обновлять задачу
                    job_args = [bot, telegram_id, event.get('summary', '(Без названия)'), event_time_str, event_link]
                    existing_job = scheduler.get_job(job_id)
                    
                    need_update = True
                    if existing_job:
                        # Сравниваем время и аргументы. next_run_time может быть None или отсутствовать в некоторых случаях
                        existing_run_time = getattr(existing_job, 'next_run_time', None)
                        if existing_run_time == trigger_dt and list(existing_job.args) == job_args:
                            need_update = False
                    
                    if need_update:
                        scheduler.add_job(
                            send_reminder,
                            'date',
                            run_date=trigger_dt,
                            args=job_args,
                            id=job_id,
                            replace_existing=True
                        )
        
        except TokenRevokedError:
            logger.warning(f"Доступ пользователя {telegram_id} отозван. Пропуск синхронизации.")
        except Exception as e:
            logger.error(f"Ошибка при синхронизации календаря {telegram_id}: {e}")
    
    # Удаляем задачи, которых больше нет в календарях или которые уже прошли
    for job in scheduler.get_jobs():
        if job.id.startswith("remind_") and job.id not in all_current_job_ids:
            scheduler.remove_job(job.id)
            logger.info(f"Удалена устаревшая задача {job.id}")
    
    logger.info("Синхронизация календарей завершена.")
