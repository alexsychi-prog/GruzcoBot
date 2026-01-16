from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Callable, Awaitable, Any
from bot.services.user_service import UserService
from bot.database.database import get_session
import logging

logger = logging.getLogger(__name__)


class RoleMiddleware(BaseMiddleware):
    """Middleware для проверки ролей пользователей"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any]
    ) -> Any:
        user = None
        if hasattr(event, "from_user") and event.from_user:
            async for session in get_session():
                user = await UserService.get_or_create_user(
                    session,
                    telegram_id=event.from_user.id,
                    username=event.from_user.username,
                    first_name=event.from_user.first_name,
                    last_name=event.from_user.last_name
                )
                break
        
        if user:
            data["user"] = user
            data["is_admin"] = user.role == "admin"
        
        return await handler(event, data)

