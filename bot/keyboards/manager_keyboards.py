from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List
from bot.database.models import Task


def get_manager_menu() -> InlineKeyboardMarkup:
    """Главное меню менеджера"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Мои задачи", callback_data="manager_my_tasks")]
    ])
    return keyboard


def get_tasks_keyboard(tasks: List[Task], page: int = 0, per_page: int = 10) -> InlineKeyboardMarkup:
    """Клавиатура со списком задач"""
    buttons = []
    start = page * per_page
    end = start + per_page
    page_tasks = tasks[start:end]
    
    for task in page_tasks:
        task_text = task.text[:30] + "..." if len(task.text) > 30 else task.text
        deadline_str = task.deadline.strftime("%d.%m.%Y")
        buttons.append([
            InlineKeyboardButton(
                text=f"📌 {task_text} (до {deadline_str})",
                callback_data=f"task_{task.id}"
            )
        ])
    
    # Пагинация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"tasks_page_{page-1}"))
    if end < len(tasks):
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"tasks_page_{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_task_actions_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Клавиатура с действиями для задачи"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ ВЫПОЛНЕНО", callback_data=f"task_complete_{task_id}"),
            InlineKeyboardButton(text="❌ НЕ ВЫПОЛНЕНО", callback_data=f"task_not_complete_{task_id}")
        ],
        [InlineKeyboardButton(text="◀️ Назад к задачам", callback_data="manager_my_tasks")]
    ])
    return keyboard

