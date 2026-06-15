
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import datetime
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.services.scheduler import check_calendars, MONTHS_RU
from aiogram import Bot

@pytest.fixture
def local_scheduler():
    s = AsyncIOScheduler()
    return s

@pytest.mark.asyncio
async def test_check_calendars_no_duplicates(local_scheduler):
    local_scheduler.start()
    try:
        # Mock bot
        bot = MagicMock(spec=Bot)
        
        # Mock database
        mock_reminders = [(12345, 10)] # telegram_id, reminder_minutes
        
        # Mock calendar service
        now_utc = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
        trigger_dt = now_utc + datetime.timedelta(minutes=30)
        start_dt = trigger_dt + datetime.timedelta(minutes=10) # reminder_minutes = 10
        
        mock_service = MagicMock()
        mock_events = {
            'items': [
                {
                    'id': 'event1',
                    'summary': 'Test Event',
                    'start': {'dateTime': start_dt.isoformat()},
                    'htmlLink': 'http://example.com'
                }
            ]
        }
        mock_service.events().list().execute.return_value = mock_events
        
        with patch('src.services.scheduler.get_all_reminders', AsyncMock(return_value=mock_reminders)), \
             patch('src.services.scheduler.get_calendar_service', AsyncMock(return_value=mock_service)), \
             patch('src.services.scheduler.scheduler', local_scheduler):
            
            # First run - should add job
            await check_calendars(bot)
            jobs = local_scheduler.get_jobs()
            assert len(jobs) == 1
            job = jobs[0]
            assert job.id == "remind_12345_event1"
            
            # Second run - should NOT add job again (should be no-op)
            with patch.object(local_scheduler, 'add_job', wraps=local_scheduler.add_job) as mock_add_job:
                await check_calendars(bot)
                assert mock_add_job.call_count == 0
            
            # Modify event summary - should update job
            mock_events['items'][0]['summary'] = 'Updated Event'
            with patch.object(local_scheduler, 'add_job', wraps=local_scheduler.add_job) as mock_add_job:
                await check_calendars(bot)
                assert mock_add_job.call_count == 1
                assert local_scheduler.get_job("remind_12345_event1").args[2] == 'Updated Event'
    finally:
        local_scheduler.shutdown()

@pytest.mark.asyncio
async def test_check_calendars_cleanup(local_scheduler):
    local_scheduler.start()
    try:
        # Mock bot
        bot = MagicMock(spec=Bot)
        
        # Initial state: 2 jobs
        mock_reminders = [(12345, 10)]
        now_utc = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
        
        mock_service = MagicMock()
        mock_events = {
            'items': [
                {
                    'id': 'event1',
                    'summary': 'Event 1',
                    'start': {'dateTime': (now_utc + datetime.timedelta(minutes=40)).isoformat()},
                },
                {
                    'id': 'event2',
                    'summary': 'Event 2',
                    'start': {'dateTime': (now_utc + datetime.timedelta(minutes=70)).isoformat()},
                }
            ]
        }
        mock_service.events().list().execute.return_value = mock_events
        
        with patch('src.services.scheduler.get_all_reminders', AsyncMock(return_value=mock_reminders)), \
             patch('src.services.scheduler.get_calendar_service', AsyncMock(return_value=mock_service)), \
             patch('src.services.scheduler.scheduler', local_scheduler):
                    
            await check_calendars(bot)
            assert len(local_scheduler.get_jobs()) == 2
            
            # Second run: one event removed from calendar
            mock_events['items'].pop(0)
            await check_calendars(bot)
            
            jobs = local_scheduler.get_jobs()
            assert len(jobs) == 1
            assert jobs[0].id == "remind_12345_event2"
    finally:
        local_scheduler.shutdown()
