"""
Обработчики команд Telegram бота для управления календарем.
"""
import logging
from aiogram import Router, F
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.services.db import get_reminder, save_reminder, user_exists
from src.services.auth import get_google_auth_url, process_auth_response
from src.services.calendar import get_past_events, get_upcoming_events, format_events, TokenRevokedError

router = Router()
logger = logging.getLogger(__name__)

class AuthStates(StatesGroup):
    waiting_for_auth_url = State()

@router.message(Command("start"))
async def start_command(message: Message, state: FSMContext):
    """Обработчик команды /start - приветствие и авторизация"""
    user_id = message.from_user.id

    if await user_exists(user_id):
        await message.answer(
            f"👋 Привет, {message.from_user.first_name}! Рад тебя видеть снова.\n\n"
            "Используй команду /events, чтобы увидеть свои ближайшие события.\n"
            "Используй команду /set_reminder, чтобы установить напоминание.\n"
            "Используй команду /show_reminder, чтобы увидеть текущее напоминание.\n"
            "Используй команду /history, чтобы увидеть историю событий.\n\n"
            "Если у тебя возникли проблемы с доступом, используй /reauth для переподключения."
        )
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
            "4. <b>Скопируй всю ссылку</b> из адресной строки и пришли её мне.",
            parse_mode="HTML",
            disable_web_page_preview=True
        )

@router.message(Command("reauth"))
async def reauth_command(message: Message, state: FSMContext):
    """Обработчик команды /reauth - принудительное переподключение Google аккаунта"""
    auth_url, code_verifier = await get_google_auth_url()
    await state.update_data(code_verifier=code_verifier)
    await state.set_state(AuthStates.waiting_for_auth_url)
    await message.answer(
        "🔄 <b>Переподключение Google Calendar</b>\n\n"
        "Это поможет, если бот потерял доступ к твоему календарю.\n\n"
        "1. Перейди по ссылке: " + auth_url + "\n"
        "2. Авторизуйся и разреши доступ.\n"
        "3. Скопируй ссылку из адресной строки (localhost) и пришли её мне сюда.",
        parse_mode="HTML",
        disable_web_page_preview=True
    )

@router.message(Command("events"))
async def events_command(message: Message):
    """Обработчик команды /events - показ ближайших событий"""
    user_id = message.from_user.id

    # Сначала проверяем, авторизован ли пользователь
    if not await user_exists(user_id):
        await message.answer("❌ Вы не авторизованы. Введите /start для подключения календаря.")
        return

    wait_message = await message.answer("🔄 Получаю данные из календаря...")

    try:
        events = await get_upcoming_events(user_id, max_results=5)

        if events is None:
            await wait_message.edit_text("❌ Ошибка при получении событий. Попробуйте позже.")
        else:
            formatted_text = format_events(events, title="Ваши ближайшие события")
            await wait_message.edit_text(formatted_text, parse_mode="Markdown")
    except TokenRevokedError:
        await wait_message.edit_text(
            "❌ Доступ к Google Calendar отозван или недействителен.\n"
            "Пожалуйста, выполните повторную авторизацию с помощью команды /reauth."
        )
    except Exception as e:
        logger.error(f"Ошибка в events_command: {e}")
        await wait_message.edit_text("❌ Произошла непредвиденная ошибка.")

@router.message(Command("set_reminder"))
async def set_reminder(message: Message, command: CommandObject):
    """Пример обработчика для установки напоминания"""
    user_id = message.from_user.id
    valid_reminder = command.args and command.args.isdigit() and int(command.args) > 0 and int(command.args) <= 1440  # Ограничение от 1 до 1440 минут (24 часа)
    if not valid_reminder:
        reminder = "30"  # Если аргументов нет или они не цифры, по умолчанию 30 минут
    else:
        reminder = command.args

    # Сначала проверяем, авторизован ли пользователь
    if not await user_exists(user_id):
        await message.answer("❌ Вы не авторизованы. Введите /start для подключения календаря.")
        return
    
    await save_reminder(message.from_user.id, reminder)

    if not valid_reminder:
        await message.answer(f"Напоминание установлено по умолчанию: {reminder} минут!")
        return
    await message.answer(f"Напоминание '{reminder}' установлено!")

@router.message(Command("show_reminder"))
async def show_reminder(message: Message):
    """Пример обработчика для показа текущего напоминания"""
    user_id = message.from_user.id

    # Сначала проверяем, авторизован ли пользователь
    if not await user_exists(user_id):
        await message.answer("❌ Вы не авторизованы. Введите /start для подключения календаря.")
        return

    current_reminder = await get_reminder(message.from_user.id)
    await message.answer(f"Напоминание установлено каждые '{current_reminder}' минут!") 

@router.message(Command("history"))
async def show_history(message: Message):
    """Обработчик команды /history - показ последних 10 прошедших событий"""
    user_id = message.from_user.id

    # Сначала проверяем, авторизован ли пользователь
    if not await user_exists(user_id):
        await message.answer("❌ Вы не авторизованы. Введите /start для подключения календаря.")
        return
    
    wait_message = await message.answer("🔄 Загружаю историю событий...")
    
    try:
        past_events = await get_past_events(user_id, max_results=10)

        if past_events is None:
            await wait_message.edit_text("❌ Ошибка при получении истории событий.")
        else:
            formatted_text = format_events(past_events, title="Ваши последние 10 событий")
            await wait_message.edit_text(formatted_text, parse_mode="Markdown")
    except TokenRevokedError:
        await wait_message.edit_text(
            "❌ Доступ к Google Calendar отозван или недействителен.\n"
            "Пожалуйста, выполните повторную авторизацию с помощью команды /reauth."
        )
    except Exception as e:
        logger.error(f"Ошибка в show_history: {e}")
        await wait_message.edit_text("❌ Произошла непредвиденная ошибка.")

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