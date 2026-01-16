from bot.database.models import Task
from typing import List
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

EXPORTS_DIR = "exports"


class FileService:
    @staticmethod
    async def save_completed_tasks_to_file(tasks: List[Task]) -> str:
        """Сохранить выполненные задачи в TXT файл"""
        if not os.path.exists(EXPORTS_DIR):
            os.makedirs(EXPORTS_DIR)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Используем os.path.join для правильного формирования пути в Windows
        filename = os.path.join(EXPORTS_DIR, f"completed_tasks_{timestamp}.txt")
        # Получаем абсолютный путь
        abs_path = os.path.abspath(filename)
        
        try:
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write("=" * 60 + "\n")
                f.write(f"ВЫПОЛНЕННЫЕ ЗАДАЧИ (Экспорт: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')})\n")
                f.write("=" * 60 + "\n\n")
                
                if not tasks:
                    f.write("Нет задач для экспорта.\n")
                else:
                    for task in tasks:
                        manager_name = task.manager.first_name or task.manager.username or f"ID: {task.manager.telegram_id}" if task.manager else "N/A"
                        completed_at = task.completed_at.strftime("%d.%m.%Y %H:%M:%S") if task.completed_at else "N/A"
                        
                        f.write(f"Менеджер: {manager_name}\n")
                        f.write(f"Задача: {task.text}\n")
                        f.write(f"Дата выполнения: {completed_at}\n")
                        f.write("-" * 60 + "\n\n")
            
            logger.info(f"Saved {len(tasks)} completed tasks to {abs_path}")
            return abs_path  # Возвращаем абсолютный путь
        except Exception as e:
            logger.error(f"Error saving tasks to file: {e}", exc_info=True)
            raise

