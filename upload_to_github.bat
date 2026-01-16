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

REM Добавление всех файлов
echo Добавление файлов...
git add .
echo.

REM Создание коммита
echo Создание коммита...
git commit -m "Initial commit: GruzcoBot - Telegram Bot для управления задачами"
echo.

REM Переименование ветки в main (если нужно)
echo Настройка ветки...
git branch -M main
echo.

REM Push на GitHub
echo ========================================
echo Загрузка на GitHub...
echo ========================================
echo.
echo Введите данные:
echo   Username: alexsychi-prog
echo   Password: [ваш Personal Access Token]
echo.
git push -u origin main

if errorlevel 1 (
    echo.
    echo ОШИБКА при загрузке!
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
