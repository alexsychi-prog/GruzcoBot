@echo off
chcp 65001 >nul
echo ========================================
echo Установка и запуск GruzcoBot
echo ========================================
echo.

REM Проверка наличия Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Python не установлен!
    echo Установите Python 3.11+ с https://www.python.org/
    pause
    exit /b 1
)

REM Создание виртуального окружения (если еще не создано)
if not exist venv (
    echo Создание виртуального окружения...
    python -m venv venv
    echo.
)

REM Активация виртуального окружения
echo Активация виртуального окружения...
call venv\Scripts\activate.bat
echo.

REM Установка зависимостей
echo Установка зависимостей...
pip install -r requirements.txt
echo.

REM Проверка наличия .env файла
if not exist .env (
    echo ========================================
    echo ВНИМАНИЕ: Файл .env не найден!
    echo ========================================
    echo.
    echo Создайте файл .env в корне проекта со следующим содержимым:
    echo.
    echo BOT_TOKEN=ваш_токен_от_BotFather
    echo ADMIN_TELEGRAM_ID=ваш_telegram_id
    echo DATABASE_URL=sqlite+aiosqlite:///data/bot.db
    echo LOG_LEVEL=INFO
    echo.
    echo Получите токен у @BotFather в Telegram
    echo Получите ID у @userinfobot в Telegram
    echo.
    pause
    exit /b 1
)

echo ========================================
echo Запуск бота...
echo ========================================
echo.
python -m bot.main

pause

