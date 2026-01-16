@echo off
chcp 65001 >nul
echo Остановка старых процессов...
taskkill /F /IM python.exe 2>nul
timeout /t 2 /nobreak >nul
echo Запуск бота...
cd /d "%~dp0"
python -m bot.main
pause

