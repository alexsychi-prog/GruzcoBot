from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.database.models import User
from bot.config import settings
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class UserService:
    @staticmethod
    async def get_or_create_user(
        session: AsyncSession,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> User:
        """Получить или создать пользователя"""
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            role = "admin" if telegram_id == settings.ADMIN_TELEGRAM_ID else "manager"
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                role=role
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            logger.info(f"Created new user: {telegram_id} with role: {role}")
        else:
            # Обновляем данные пользователя
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            await session.commit()
        
        return user
    
    @staticmethod
    async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
        """Получить пользователя по Telegram ID"""
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_all_managers(session: AsyncSession) -> List[User]:
        """Получить всех менеджеров"""
        result = await session.execute(
            select(User).where(User.role == "manager")
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def is_admin(telegram_id: int) -> bool:
        """Проверить, является ли пользователь администратором"""
        return telegram_id == settings.ADMIN_TELEGRAM_ID

