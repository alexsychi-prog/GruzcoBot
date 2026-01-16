from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case
from sqlalchemy.orm import selectinload
from bot.database.models import Task, User
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import logging

logger = logging.getLogger(__name__)


class TaskService:
    @staticmethod
    async def create_task(
        session: AsyncSession,
        manager_id: int,
        text: str,
        deadline: datetime
    ) -> Task:
        """Создать новую задачу"""
        task = Task(
            manager_id=manager_id,
            text=text,
            deadline=deadline,
            status="active"
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        logger.info(f"Created task {task.id} for manager {manager_id}")
        return task
    
    @staticmethod
    async def get_active_tasks_by_manager(session: AsyncSession, manager_id: int) -> List[Task]:
        """Получить активные задачи менеджера"""
        result = await session.execute(
            select(Task)
            .where(and_(Task.manager_id == manager_id, Task.status == "active"))
            .order_by(Task.deadline.asc())
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_task_by_id(session: AsyncSession, task_id: int) -> Optional[Task]:
        """Получить задачу по ID"""
        result = await session.execute(select(Task).where(Task.id == task_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def complete_task(session: AsyncSession, task_id: int) -> Optional[Task]:
        """Отметить задачу как выполненную"""
        task = await TaskService.get_task_by_id(session, task_id)
        if task:
            task.status = "completed"
            task.completed_at = datetime.utcnow()
            await session.commit()
            await session.refresh(task)
            logger.info(f"Task {task_id} marked as completed")
        return task
    
    @staticmethod
    async def update_task_deadline(
        session: AsyncSession,
        task_id: int,
        new_deadline: datetime,
        reason: str
    ) -> Optional[Task]:
        """Обновить дедлайн задачи"""
        task = await TaskService.get_task_by_id(session, task_id)
        if task:
            task.deadline = new_deadline
            task.not_completed_reason = reason
            task.status = "active"
            task.updated_at = datetime.utcnow()
            await session.commit()
            await session.refresh(task)
            logger.info(f"Task {task_id} deadline updated to {new_deadline}")
        return task
    
    @staticmethod
    async def get_all_tasks(session: AsyncSession) -> List[Task]:
        """Получить все задачи"""
        result = await session.execute(
            select(Task)
            .options(selectinload(Task.manager))
            .order_by(Task.created_at.desc())
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_completed_tasks_older_than_with_manager(session: AsyncSession, days: int = 7) -> List[Task]:
        """Получить выполненные задачи старше N дней с загруженным менеджером"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        result = await session.execute(
            select(Task)
            .options(selectinload(Task.manager))
            .where(
                and_(
                    Task.status == "completed",
                    Task.completed_at.isnot(None),  # Убеждаемся, что completed_at не NULL
                    Task.completed_at < cutoff_date
                )
            )
        )
        tasks = list(result.scalars().all())
        logger.info(f"Found {len(tasks)} completed tasks older than {days} days with manager loaded (cutoff: {cutoff_date})")
        return tasks
    
    @staticmethod
    async def get_tasks_due_today(session: AsyncSession) -> List[Task]:
        """Получить задачи с дедлайном сегодня"""
        today = datetime.utcnow().date()
        result = await session.execute(
            select(Task).where(
                and_(
                    func.date(Task.deadline) == today,
                    Task.status == "active"
                )
            )
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_completed_tasks_older_than(
        session: AsyncSession,
        days: int = 7
    ) -> List[Task]:
        """Получить выполненные задачи старше N дней"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        result = await session.execute(
            select(Task).where(
                and_(
                    Task.status == "completed",
                    Task.completed_at.isnot(None),  # Убеждаемся, что completed_at не NULL
                    Task.completed_at < cutoff_date
                )
            )
        )
        tasks = list(result.scalars().all())
        logger.info(f"Found {len(tasks)} completed tasks older than {days} days (cutoff: {cutoff_date})")
        return tasks
    
    @staticmethod
    async def delete_tasks(session: AsyncSession, task_ids: List[int]) -> int:
        """Удалить задачи по списку ID"""
        result = await session.execute(
            select(Task).where(Task.id.in_(task_ids))
        )
        tasks = result.scalars().all()
        for task in tasks:
            await session.delete(task)
        await session.commit()
        logger.info(f"Deleted {len(tasks)} tasks")
        return len(tasks)
    
    @staticmethod
    async def get_manager_statistics(session: AsyncSession) -> List[Dict]:
        """Получить статистику по менеджерам"""
        result = await session.execute(
            select(
                User.id,
                User.first_name,
                User.username,
                func.count(Task.id).label("total_tasks"),
                func.sum(case((Task.status == "completed", 1), else_=0)).label("completed"),
                func.sum(case((Task.status == "not_completed", 1), else_=0)).label("not_completed")
            )
            .outerjoin(Task, User.id == Task.manager_id)
            .where(User.role == "manager")
            .group_by(User.id, User.first_name, User.username)
        )
        
        stats = []
        for row in result.all():
            total = row.total_tasks or 0
            completed = int(row.completed or 0)
            not_completed = int(row.not_completed or 0)
            percentage = (completed / total * 100) if total > 0 else 0
            
            stats.append({
                "user_id": row.id,
                "name": row.first_name or row.username or f"ID: {row.id}",
                "total": total,
                "completed": completed,
                "not_completed": not_completed,
                "percentage": round(percentage, 2)
            })
        
        # Сортируем по проценту выполнения (лучшие первыми)
        stats.sort(key=lambda x: (x["percentage"], x["completed"]), reverse=True)
        return stats
    
    @staticmethod
    async def get_detailed_manager_statistics(session: AsyncSession) -> List[Dict]:
        """Получить детальную статистику по менеджерам с активными задачами"""
        result = await session.execute(
            select(
                User.id,
                User.first_name,
                User.username,
                User.telegram_id,
                func.count(Task.id).label("total_tasks"),
                func.sum(case((Task.status == "completed", 1), else_=0)).label("completed"),
                func.sum(case((Task.status == "not_completed", 1), else_=0)).label("not_completed"),
                func.sum(case((Task.status == "active", 1), else_=0)).label("active")
            )
            .outerjoin(Task, User.id == Task.manager_id)
            .where(User.role == "manager")
            .group_by(User.id, User.first_name, User.username, User.telegram_id)
        )
        
        stats = []
        for row in result.all():
            total = row.total_tasks or 0
            completed = int(row.completed or 0)
            not_completed = int(row.not_completed or 0)
            active = int(row.active or 0)
            percentage = (completed / total * 100) if total > 0 else 0
            
            stats.append({
                "user_id": row.id,
                "telegram_id": row.telegram_id,
                "name": row.first_name or row.username or f"ID: {row.telegram_id}",
                "total": total,
                "completed": completed,
                "not_completed": not_completed,
                "active": active,
                "percentage": round(percentage, 2)
            })
        
        # Сортируем по имени
        stats.sort(key=lambda x: x["name"])
        return stats

