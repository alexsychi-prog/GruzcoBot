from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.database.models import GroupAnalytics, GroupMember
from typing import Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AnalyticsService:
    @staticmethod
    async def get_or_create_group_analytics(
        session: AsyncSession,
        group_id: int,
        group_title: Optional[str] = None
    ) -> GroupAnalytics:
        """Получить или создать аналитику группы"""
        result = await session.execute(
            select(GroupAnalytics).where(GroupAnalytics.group_id == group_id)
        )
        analytics = result.scalar_one_or_none()
        
        if not analytics:
            analytics = GroupAnalytics(
                group_id=group_id,
                group_title=group_title,
                total_members=0
            )
            session.add(analytics)
            await session.commit()
            await session.refresh(analytics)
            logger.info(f"Created analytics for group {group_id}")
        
        return analytics
    
    @staticmethod
    async def update_group_members(
        session: AsyncSession,
        group_id: int,
        current_members: List[dict]
    ):
        """Обновить список участников группы"""
        analytics = await AnalyticsService.get_or_create_group_analytics(
            session, group_id
        )
        
        result = await session.execute(
            select(GroupMember).where(GroupMember.group_id == analytics.id)
        )
        db_members = {m.telegram_id: m for m in result.scalars().all()}
        
        current_member_ids = {m.get("id") for m in current_members if m.get("id")}
        
        analytics.total_members = len(current_members)
        
        for db_member in db_members.values():
            if db_member.telegram_id not in current_member_ids:
                if db_member.status == "active":
                    db_member.status = "left"
                    db_member.left_at = datetime.utcnow()
                    analytics.left_members += 1
        
        for member_data in current_members:
            member_id = member_data.get("id")
            if member_id and member_id not in db_members:
                new_member = GroupMember(
                    group_id=analytics.id,
                    telegram_id=member_id,
                    username=member_data.get("username"),
                    first_name=member_data.get("first_name"),
                    status="active"
                )
                session.add(new_member)
        
        analytics.last_updated = datetime.utcnow()
        await session.commit()
        logger.info(f"Updated members for group {group_id}")
    
    @staticmethod
    async def get_group_analytics(session: AsyncSession, group_id: int) -> Optional[GroupAnalytics]:
        """Получить аналитику группы"""
        result = await session.execute(
            select(GroupAnalytics).where(GroupAnalytics.group_id == group_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_left_members(session: AsyncSession, analytics_id: int) -> List[GroupMember]:
        """Получить список вышедших участников"""
        result = await session.execute(
            select(GroupMember).where(
                GroupMember.group_id == analytics_id,
                GroupMember.status.in_(["left", "kicked"])
            )
        )
        return list(result.scalars().all())

