from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List
from bot.database.models import User


def get_admin_menu() -> InlineKeyboardMarkup:
    """Главное меню администратора"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣ ДОБАВИТЬ ЗАДАЧУ", callback_data="admin_add_task")],
        [InlineKeyboardButton(text="2️⃣ СПИСОК ВСЕХ ЗАДАЧ", callback_data="admin_all_tasks")],
        [InlineKeyboardButton(text="3️⃣ АНАЛИЗ TELEGRAM-ГРУПП", callback_data="admin_group_analysis")],
        [InlineKeyboardButton(text="4️⃣ РЕЙТИНГ МЕНЕДЖЕРОВ", callback_data="admin_rating")],
        [InlineKeyboardButton(text="5️⃣ ОЧИСТКА ВЫПОЛНЕННЫХ ЗАДАЧ", callback_data="admin_cleanup")],
        [InlineKeyboardButton(text="6️⃣ ВСЕ СОТРУДНИКИ", callback_data="admin_all_employees")]
    ])
    return keyboard


def get_manager_list_keyboard(managers: List[User]) -> InlineKeyboardMarkup:
    """Клавиатура со списком менеджеров"""
    buttons = []
    for manager in managers:
        name = manager.first_name or manager.username or f"ID: {manager.telegram_id}"
        buttons.append([
            InlineKeyboardButton(
                text=name,
                callback_data=f"select_manager_{manager.id}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="◀️ Отмена", callback_data="admin_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

