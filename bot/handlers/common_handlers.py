from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from bot.keyboards.admin_keyboards import get_admin_menu
from bot.keyboards.manager_keyboards import get_manager_menu
import logging

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, user=None, is_admin=False):
    """Обработчик команды /start"""
    logger.info(f"Received /start from user {message.from_user.id}, is_admin={is_admin}")
    try:
        if is_admin:
            text = "👋 Добро пожаловать, администратор!\n\nВыберите действие:"
            await message.answer(text, reply_markup=get_admin_menu())
        else:
            text = "👋 Добро пожаловать!\n\nВыберите действие:"
            await message.answer(text, reply_markup=get_manager_menu())
        logger.info(f"Successfully sent menu to user {message.from_user.id}")
    except Exception as e:
        logger.error(f"Error in cmd_start: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, user=None, is_admin=None):
    """Возврат в главное меню"""
    await callback.answer()
    if is_admin:
        text = "👋 Главное меню администратора"
        await callback.message.edit_text(text, reply_markup=get_admin_menu())
    else:
        text = "👋 Главное меню"
        await callback.message.edit_text(text, reply_markup=get_manager_menu())

