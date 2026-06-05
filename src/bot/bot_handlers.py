"""
Обработчики команд Telegram бота для управления календарем.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime

from services.db import user_exists
from config import settings
from src.services.auth import get_google_auth_url

router = Router()

@router.message(Command("start"))
async def start_command(message: Message):
    """Обработчик команды /start - приветствие"""
    welcome_text = (
        "🎉 Привет! Я бот для управления календарем."
    )

    user_exists_result = await user_exists(message.from_user.id)
    if not user_exists_result:
        auth_url = await get_google_auth_url()
        welcome_text += (f"\n\nДля начала работы, пожалуйста, авторизуйтесь через Google: {auth_url}")
    await message.answer(welcome_text)