# Скрипт для остановки всех запущенных экземпляров бота

Write-Host "Поиск запущенных процессов бота..." -ForegroundColor Yellow

# Находим все процессы Python, которые могут быть ботом
$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue

if ($pythonProcesses) {
    Write-Host "Найдено процессов Python: $($pythonProcesses.Count)" -ForegroundColor Cyan
    
    # Останавливаем все процессы Python (осторожно!)
    foreach ($proc in $pythonProcesses) {
        try {
            Write-Host "Останавливаю процесс ID: $($proc.Id)" -ForegroundColor Yellow
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            Write-Host "Процесс $($proc.Id) остановлен" -ForegroundColor Green
        } catch {
            Write-Host "Не удалось остановить процесс $($proc.Id): $_" -ForegroundColor Red
        }
    }
    
    Write-Host "`nВсе процессы Python остановлены!" -ForegroundColor Green
    Write-Host "Подождите 3 секунды перед повторным запуском..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
} else {
    Write-Host "Процессы Python не найдены" -ForegroundColor Green
}

Write-Host "`nТеперь можно запустить бота командой: python -m bot.main" -ForegroundColor Cyan

