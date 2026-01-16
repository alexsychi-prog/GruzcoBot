@echo off
chcp 65001 >nul
echo ========================================
echo Загрузка проекта GruzcoBot на GitHub
echo ========================================
echo.

REM Инициализация репозитория (если еще не инициализирован)
if not exist .git (
    echo Инициализация Git репозитория...
    git init
    echo.
)

REM Добавление remote (удаляем старый, если есть, и добавляем новый)
echo Настройка remote репозитория...
git remote remove origin 2>nul
git remote add origin https://github.com/alexsychi-prog/GruzcoBot.git
echo.

REM Получение изменений с GitHub (если есть)
echo Получение изменений с GitHub...
git fetch origin
echo.

REM Добавление всех файлов
echo Добавление файлов...
git add .
echo.

REM Создание коммита
echo Создание коммита...
git commit -m "Initial commit: GruzcoBot - Telegram Bot для управления задачами" 2>nul
if errorlevel 1 (
    echo Коммит уже существует или нет изменений.
    echo.
)

REM Переименование ветки в main (если нужно)
echo Настройка ветки...
git branch -M main
echo.

REM Попытка синхронизации с удаленным репозиторием
echo Попытка синхронизации с GitHub...
git pull origin main --allow-unrelated-histories --no-edit 2>nul
if errorlevel 1 (
    echo.
    echo Обнаружены конфликты или различия в истории.
    echo Применяется стратегия объединения...
    echo.
)

REM Push на GitHub с force (перезапись удаленного репозитория)
echo ========================================
echo Загрузка на GitHub...
echo ========================================
echo.
echo ВАЖНО: Это перезапишет содержимое на GitHub текущим проектом!
echo.
echo Введите данные:
echo   Username: alexsychi-prog
echo   Password: [ваш Personal Access Token]
echo.
git push -u origin main --force

if errorlevel 1 (
    echo.
    echo ========================================
    echo ОШИБКА при загрузке!
    echo ========================================
    echo.
    echo Возможные причины:
    echo   1. Неправильный токен
    echo   2. Нет прав доступа
    echo.
) else (
    echo.
    echo ========================================
    echo УСПЕШНО! Проект загружен на GitHub
    echo ========================================
    echo.
    echo https://github.com/alexsychi-prog/GruzcoBot
    echo.
)

pause
