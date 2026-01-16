@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo Обновление проекта на GitHub
echo ========================================
echo.

REM Добавление всех изменений
git add .

REM Создание коммита
git commit -m "Update README and add setup instructions" 2>nul
if errorlevel 1 (
    echo Нет изменений для коммита или коммит уже существует.
    echo.
)

REM Push на GitHub
echo Загрузка на GitHub...
git push origin main

if errorlevel 1 (
    echo.
    echo ОШИБКА при загрузке!
    echo Проверьте подключение и токен.
) else (
    echo.
    echo ========================================
    echo УСПЕШНО! Изменения загружены
    echo ========================================
    echo.
    echo https://github.com/alexsychi-prog/GruzcoBot
    echo.
)

pause

