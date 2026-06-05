"""
Обработчики команд Telegram бота для управления календарем.
"""
import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.services.db import user_exists
from src.services.auth import get_google_auth_url, process_auth_response

router = Router()
logger = logging.getLogger(__name__)

class AuthStates(StatesGroup):
    waiting_for_auth_url = State()

@router.message(Command("start"))
async def start_command(message: Message, state: FSMContext):
    """Обработчик команды /start - приветствие и авторизация"""
    user_id = message.from_user.id

    if await user_exists(user_id):
        await message.answer(f"👋 Привет, {message.from_user.first_name}! Рад тебя видеть снова.")
    else:
        auth_url, code_verifier = await get_google_auth_url()
        # Сохраняем verifier в состоянии, чтобы использовать его при проверке ссылки
        await state.update_data(code_verifier=code_verifier)
        await state.set_state(AuthStates.waiting_for_auth_url)
        await message.answer(
            "🎉 Привет! Я бот для управления календарем.\n\n"
            "🔑 Для работы мне нужен доступ к твоему Google Calendar.\n\n"
            "1. Перейди по ссылке: " + auth_url + "\n"
            "2. Авторизуйся и разреши доступ.\n"
            "3. Тебя перекинет на страницу, которая не откроется (localhost) — это нормально.\n"
            "4. **Скопируй всю ссылку** из адресной строки и пришли её мне."
        )

@router.message(AuthStates.waiting_for_auth_url)
async def handle_auth_url(message: Message, state: FSMContext):
    """Обработка ссылки авторизации от пользователя"""
    logger.info(f"Получено сообщение в состоянии waiting_for_auth_url: {message.text[:50]}...")
    
    if not message.text or not message.text.startswith("http"):
        await message.answer("❌ Пожалуйста, пришли корректную ссылку, начинающуюся с http")
        return

    # Извлекаем сохраненный verifier
    user_data = await state.get_data()
    code_verifier = user_data.get("code_verifier")
    logger.info(f"Code verifier найден: {bool(code_verifier)}")

    if not code_verifier:
        await message.answer("❌ Сессия устарела. Пожалуйста, введите /start еще раз.")
        await state.clear()
        return

    success = await process_auth_response(
        message.from_user.id, 
        message.from_user.username or "Unknown", 
        message.text,
        code_verifier
    )

    if success:
        await message.answer("✅ Авторизация успешна! Теперь я могу управлять твоим календарем.")
        await state.clear()
    else:
        await message.answer("❌ Ошибка при обработке ссылки. Попробуй еще раз или проверь ссылку.")