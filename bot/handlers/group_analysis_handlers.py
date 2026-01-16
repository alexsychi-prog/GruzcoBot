from aiogram import Router, F, Bot
from aiogram.types import Message, ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter, IS_MEMBER, IS_NOT_MEMBER, KICKED, LEFT
from bot.services.analytics_service import AnalyticsService
from bot.database.database import get_session
from bot.database.models import GroupMember
from sqlalchemy import select
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = Router()


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> IS_MEMBER))
async def bot_added_to_group(event: ChatMemberUpdated, bot):
    """Бот добавлен в группу"""
    chat = event.chat
    if chat.type in ["group", "supergroup"]:
        async for session in get_session():
            analytics = await AnalyticsService.get_or_create_group_analytics(
                session,
                group_id=chat.id,
                group_title=chat.title
            )
            
            # Получаем текущее количество участников
            try:
                member_count = await bot.get_chat_member_count(chat.id)
                analytics.total_members = member_count
                await session.commit()
                logger.info(f"Bot added to group {chat.id}: {chat.title}, members: {member_count}")
            except Exception as e:
                logger.error(f"Error getting member count for group {chat.id}: {e}")
            
            break


@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=IS_MEMBER >> KICKED))
async def member_kicked(event: ChatMemberUpdated, bot: Bot):
    """Участник был исключён администратором"""
    chat = event.chat
    user = event.new_chat_member.user
    new_status = event.new_chat_member.status
    old_status = event.old_chat_member.status if event.old_chat_member else None
    
    logger.info(f"Member KICKED: chat_id={chat.id}, user_id={user.id}, username={user.username}, old_status={old_status}, new_status={new_status}")
    
    if chat.type in ["group", "supergroup"]:
        async for session in get_session():
            analytics = await AnalyticsService.get_or_create_group_analytics(
                session,
                group_id=chat.id,
                group_title=chat.title
            )
            
            # Проверяем, есть ли уже запись об этом участнике
            result = await session.execute(
                select(GroupMember).where(
                    GroupMember.group_id == analytics.id,
                    GroupMember.telegram_id == user.id
                )
            )
            member = result.scalar_one_or_none()
            
            # Обновляем счетчики только если участник еще не был учтен как исключенный
            status_changed = False
            if member:
                old_db_status = member.status
                if old_db_status != "kicked":
                    status_changed = True
                    # Уменьшаем старый счетчик, если был другой статус
                    if old_db_status == "left":
                        analytics.left_members = max(0, analytics.left_members - 1)
            else:
                status_changed = True
            
            if status_changed:
                analytics.kicked_members += 1
                logger.info(f"Incrementing kicked_members for group {chat.id}, now: {analytics.kicked_members}")
            
            # Обновляем общее количество участников
            try:
                member_count = await bot.get_chat_member_count(chat.id)
                analytics.total_members = member_count
                logger.info(f"Updated total_members for group {chat.id} to {member_count}")
            except Exception as e:
                logger.error(f"Error updating member count for group {chat.id}: {e}")
                analytics.total_members = max(0, analytics.total_members - 1)
            
            if member:
                member.status = "kicked"
                if user.username:
                    member.username = user.username
                if user.first_name:
                    member.first_name = user.first_name
            else:
                member = GroupMember(
                    group_id=analytics.id,
                    telegram_id=user.id,
                    username=user.username or None,
                    first_name=user.first_name or None,
                    status="kicked"
                )
                session.add(member)
                logger.info(f"Created member record: {user.id}, username: {user.username}, status: kicked")
            
            analytics.last_updated = datetime.utcnow()
            await session.commit()
            logger.info(f"Member {user.id} KICKED from group {chat.id}")
            break


@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=IS_MEMBER >> LEFT))
async def member_left(event: ChatMemberUpdated, bot: Bot):
    """Участник сам вышел из группы"""
    chat = event.chat
    user = event.new_chat_member.user
    new_status = event.new_chat_member.status
    old_status = event.old_chat_member.status if event.old_chat_member else None
    from_user = event.from_user  # Пользователь, который инициировал изменение
    
    logger.info(f"Member LEFT: chat_id={chat.id}, user_id={user.id}, username={user.username}, old_status={old_status}, new_status={new_status}, from_user={from_user.id if from_user else None}")
    
    # ВАЖНО: Telegram API иногда отправляет "left" вместо "kicked" при исключении администратором
    # Если from_user отличается от user (исключаемого), значит это было исключение администратором
    is_actually_kicked = False
    if from_user and from_user.id != user.id:
        # Кто-то другой инициировал изменение - это исключение администратором
        is_actually_kicked = True
        logger.info(f"User {user.id} was actually KICKED by {from_user.id} (but status is 'left')")
    
    if chat.type in ["group", "supergroup"]:
        async for session in get_session():
            analytics = await AnalyticsService.get_or_create_group_analytics(
                session,
                group_id=chat.id,
                group_title=chat.title
            )
            
            # Проверяем, есть ли уже запись об этом участнике
            result = await session.execute(
                select(GroupMember).where(
                    GroupMember.group_id == analytics.id,
                    GroupMember.telegram_id == user.id
                )
            )
            member = result.scalar_one_or_none()
            
            # Определяем финальный статус
            final_status = "kicked" if is_actually_kicked else "left"
            
            # Обновляем счетчики только если участник еще не был учтен
            status_changed = False
            if member:
                old_db_status = member.status
                if old_db_status != final_status:
                    status_changed = True
                    # Уменьшаем старый счетчик, если был другой статус
                    if old_db_status == "left":
                        analytics.left_members = max(0, analytics.left_members - 1)
                    elif old_db_status == "kicked":
                        analytics.kicked_members = max(0, analytics.kicked_members - 1)
            else:
                status_changed = True
            
            if status_changed:
                if is_actually_kicked:
                    analytics.kicked_members += 1
                    logger.info(f"Incrementing kicked_members for group {chat.id}, now: {analytics.kicked_members}")
                else:
                    analytics.left_members += 1
                    logger.info(f"Incrementing left_members for group {chat.id}, now: {analytics.left_members}")
            
            # Обновляем общее количество участников
            try:
                member_count = await bot.get_chat_member_count(chat.id)
                analytics.total_members = member_count
                logger.info(f"Updated total_members for group {chat.id} to {member_count}")
            except Exception as e:
                logger.error(f"Error updating member count for group {chat.id}: {e}")
                analytics.total_members = max(0, analytics.total_members - 1)
            
            if member:
                member.status = final_status
                if user.username:
                    member.username = user.username
                if user.first_name:
                    member.first_name = user.first_name
            else:
                member = GroupMember(
                    group_id=analytics.id,
                    telegram_id=user.id,
                    username=user.username or None,
                    first_name=user.first_name or None,
                    status=final_status
                )
                session.add(member)
                logger.info(f"Created member record: {user.id}, username: {user.username}, status: {final_status}")
            
            analytics.last_updated = datetime.utcnow()
            await session.commit()
            logger.info(f"Member {user.id} {final_status.upper()} from group {chat.id} (status was 'left' but detected as kicked={is_actually_kicked})")
            break

