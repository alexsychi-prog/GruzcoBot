from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from bot.database.database import get_session
from bot.services.task_service import TaskService
from bot.services.file_service import FileService
from aiogram import Bot
import logging

logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
    
    async def send_deadline_reminders(self):
        """Отправка напоминаний о дедлайнах"""
        async for session in get_session():
            tasks = await TaskService.get_tasks_due_today(session)
            
            for task in tasks:
                try:
                    manager = task.manager
                    if manager:
                        message = (
                            f"⏰ <b>Напоминание о дедлайне!</b>\n\n"
                            f"📌 <b>Задача:</b> {task.text}\n"
                            f"📅 <b>Дедлайн:</b> {task.deadline.strftime('%d.%m.%Y %H:%M')}\n\n"
                            f"Пожалуйста, отметьте выполнение задачи."
                        )
                        
                        from bot.keyboards.manager_keyboards import get_task_actions_keyboard
                        await self.bot.send_message(
                            chat_id=manager.telegram_id,
                            text=message,
                            reply_markup=get_task_actions_keyboard(task.id),
                            parse_mode="HTML"
                        )
                        logger.info(f"Sent deadline reminder for task {task.id} to {manager.telegram_id}")
                except Exception as e:
                    logger.error(f"Error sending reminder for task {task.id}: {e}")
    
    async def auto_cleanup_completed_tasks(self):
        """Автоматическая очистка выполненных задач (если прошло 7 дней с последней очистки)"""
        async for session in get_session():
            try:
                from bot.database.models import CleanupLog
                from sqlalchemy import select
                from datetime import timedelta
                
                # Проверяем последнюю очистку
                result = await session.execute(select(CleanupLog).order_by(CleanupLog.id.desc()).limit(1))
                cleanup_log = result.scalar_one_or_none()
                
                # Если очистки не было или прошло 7 дней с последней очистки
                should_cleanup = False
                if not cleanup_log:
                    # Если никогда не было очистки, проверяем задачи старше 7 дней
                    should_cleanup = True
                else:
                    # Проверяем, прошло ли 7 дней с последней очистки
                    days_since_cleanup = (datetime.utcnow() - cleanup_log.last_cleanup_date).days
                    if days_since_cleanup >= 7:
                        should_cleanup = True
                        logger.info(f"Last cleanup was {days_since_cleanup} days ago, performing auto-cleanup")
                
                if should_cleanup:
                    # Получаем задачи с загруженным менеджером для сохранения в файл
                    old_tasks = await TaskService.get_completed_tasks_older_than_with_manager(session, days=7)
                    
                    if old_tasks:
                        # Сохраняем задачи в файл ПЕРЕД удалением
                        filename = await FileService.save_completed_tasks_to_file(old_tasks)
                        
                        task_ids = [task.id for task in old_tasks]
                        deleted_count = await TaskService.delete_tasks(session, task_ids)
                        
                        # Обновляем лог последней очистки
                        if cleanup_log:
                            cleanup_log.last_cleanup_date = datetime.utcnow()
                            cleanup_log.tasks_deleted = deleted_count
                            cleanup_log.cleanup_type = "auto"
                        else:
                            cleanup_log = CleanupLog(
                                last_cleanup_date=datetime.utcnow(),
                                tasks_deleted=deleted_count,
                                cleanup_type="auto"
                            )
                            session.add(cleanup_log)
                        
                        await session.commit()
                        logger.info(f"Auto-cleaned {deleted_count} completed tasks, saved to {filename}")
                    else:
                        logger.info("No completed tasks older than 7 days to clean up")
                else:
                    logger.info(f"Skipping auto-cleanup, last cleanup was recent")
            except Exception as e:
                logger.error(f"Error in auto-cleanup: {e}", exc_info=True)
    
    def start(self):
        """Запуск планировщика"""
        self.scheduler.add_job(
            self.send_deadline_reminders,
            CronTrigger(hour=9, minute=0),
            id="deadline_reminders",
            replace_existing=True
        )
        
        # Проверяем каждые 24 часа, нужно ли делать автоматическую очистку
        self.scheduler.add_job(
            self.auto_cleanup_completed_tasks,
            CronTrigger(hour=3, minute=0),  # Каждый день в 3:00
            id="auto_cleanup",
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("Scheduler started")
    
    def shutdown(self):
        """Остановка планировщика"""
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")

