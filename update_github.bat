@echo off
chcp 65001 >nul
echo ========================================
echo Обновление проекта на GitHub
echo ========================================
echo.

REM Добавление всех изменений
echo Добавление изменений...
git add .
echo.

REM Создание коммита
echo Создание коммита...
git commit -m "Update README and add setup instructions"
echo.

REM Push на GitHub
echo Загрузка на GitHub...
git push origin main

if errorlevel 1 (
    echo.
    echo ОШИБКА при загрузке!
) else (
    echo.
    echo ========================================
    echo УСПЕШНО! Изменения загружены на GitHub
    echo ========================================
    echo.
    echo https://github.com/alexsychi-prog/GruzcoBot
    echo.
)

pause

