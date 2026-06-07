# 📅 Telegram Calendar Manager Bot

Умный Telegram-бот для интеграции с Google Calendar. Помогает отслеживать встречи, устанавливать гибкие напоминания и просматривать историю событий.

## 🚀 Основные возможности
- **Авторизация через Google OAuth2:** Безопасное подключение вашего календаря.
- **Уведомления о встречах:** Бот автоматически проверяет календарь каждые 5 минут и присылает напоминание за выбранное вами время.
- **История событий:** Просмотр последних 10 прошедших встреч одной командой.
- **Безопасность:** Шифрование токенов доступа в базе данных (AES-256).
- **Логирование:** Полная история событий и ошибок в файлах с автоматической ротацией.

## 🛠 Технологический стек
- **Язык:** Python 3.10+
- **Фреймворк бота:** [aiogram 3.x](https://github.com/aiogram/aiogram)
- **Планировщик:** [APScheduler](https://apscheduler.readthedocs.io/)
- **API:** Google Calendar API v3
- **База данных:** SQLite
- **Безопасность:** Cryptography (Fernet)

## 📋 Команды бота
- `/start` — Приветствие и запуск процесса авторизации Google.
- `/events` — Показать ближайшие запланированные события.
- `/history` — Показать историю последних 10 завершенных встреч.
- `/set_reminder <минуты>` — Установить время напоминания до начала встречи (например, `/set_reminder 15`).
- `/show_reminder` — Показать текущую настройку времени напоминания.

---

## ⚙️ Настройка и запуск

### 1. Подготовка Google Cloud Project
1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/).
2. Создайте новый проект.
3. В разделе **APIs & Services > Library** найдите и включите **Google Calendar API**.
4. В разделе **OAuth consent screen** создайте экран согласия (тип External) и добавьте свой email в список тестовых пользователей.
5. В разделе **Credentials** создайте **OAuth 2.0 Client IDs** (тип приложения: Desktop app).
6. Скачайте JSON-файл учетных данных или скопируйте `Client ID` и `Client Secret`.

### 2. Установка зависимостей
```bash
# Клонируйте репозиторий
git clone https://github.com/your-username/calendar-manager.git
cd calendar_manager

# Создайте и активируйте виртуальное окружение
python -m venv venv
source venv/bin/activate  # Для Linux/macOS
# или
venv\Scripts\activate     # Для Windows

# Установите пакеты
pip install -r requirements.txt
```

### 3. Настройка переменных окружения
Создайте файл `.env` в корневой директории проекта на основе `.env.example`:
```env
TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather
GOOGLE_CLIENT_ID=ваш_client_id_из_google_console
GOOGLE_CLIENT_SECRET=ваш_client_secret_из_google_console
ENCRYPTION_KEY=сгенерированный_ключ_fernet
```
*Для генерации ключа шифрования можно использовать команду:*
`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

### 4. Запуск
```bash
python src/bot/bot.py
```

## 📂 Структура проекта
```text
├── src/
│   ├── bot/            # Логика Telegram-бота и хендлеры
│   ├── services/       # Сервисы (БД, Google Calendar, Планировщик)
│   ├── data/           # Файлы базы данных
│   └── config.py       # Конфигурация через Pydantic
├── logs/               # Логи приложения (app.log)
├── docs/               # Документация и спецификации
├── requirements.txt    # Зависимости проекта
└── .env                # Конфиденциальные настройки (не для git)
```