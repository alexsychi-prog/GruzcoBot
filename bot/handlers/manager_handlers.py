from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from datetime import datetime
from bot.keyboards.manager_keyboards import get_manager_menu, get_tasks_keyboard, get_task_actions_keyboard
from bot.services.task_service import TaskService
from bot.database.database import get_session
from bot.states.manager_states import ManagerStates
import logging
import re

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data == "manager_my_tasks")
async def show_my_tasks(callback: CallbackQuery, user=None):
    """Показать активные задачи менеджера"""
    await callback.answer()
    
    async for session in get_session():
        tasks = await TaskService.get_active_tasks_by_manager(session, user.id)
        
        if not tasks:
            await callback.message.edit_text(
                "✅ У вас нет активных задач!",
                reply_markup=get_manager_menu()
            )
        else:
            text = f"📋 <b>Ваши активные задачи ({len(tasks)}):</b>\n\n"
            for i, task in enumerate(tasks[:10], 1):
                deadline_str = task.deadline.strftime("%d.%m.%Y")
                text += f"{i}. {task.text[:50]}... (до {deadline_str})\n"
            
            await callback.message.edit_text(
                text,
                reply_markup=get_tasks_keyboard(tasks),
                parse_mode="HTML"
            )
        break


@router.callback_query(F.data.startswith("task_") & ~F.data.startswith("task_complete_") & ~F.data.startswith("task_not_complete_") & ~F.data.startswith("tasks_page_"))
async def show_task_details(callback: CallbackQuery, user=None):
    """Показать детали задачи"""
    await callback.answer()
    
    task_id = int(callback.data.split("_")[1])
    
    async for session in get_session():
        task = await TaskService.get_task_by_id(session, task_id)
        
        if not task or task.manager_id != user.id or task.status != "active":
            await callback.message.edit_text(
                "❌ Задача не найдена или недоступна!",
                reply_markup=get_manager_menu()
            )
            break
        
        deadline_str = task.deadline.strftime("%d.%m.%Y %H:%M")
        text = (
            f"📌 <b>Задача #{task.id}</b>\n\n"
            f"<b>Текст:</b> {task.text}\n"
            f"<b>Дедлайн:</b> {deadline_str}\n\n"
            f"Выберите действие:"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=get_task_actions_keyboard(task_id),
            parse_mode="HTML"
        )
        break


@router.callback_query(F.data.startswith("task_complete_"))
async def complete_task(callback: CallbackQuery, user=None):
    """Отметить задачу как выполненную"""
    await callback.answer()
    
    task_id = int(callback.data.split("_")[2])
    
    async for session in get_session():
        task = await TaskService.get_task_by_id(session, task_id)
        
        if not task or task.manager_id != user.id:
            await callback.message.edit_text(
                "❌ Задача не найдена!",
                reply_markup=get_manager_menu()
            )
            break
        
        await TaskService.complete_task(session, task_id)
        
        await callback.message.edit_text(
            "✅ Задача отмечена как выполненная!",
            reply_markup=get_manager_menu()
        )
        break


@router.callback_query(F.data.startswith("task_not_complete_"))
async def not_complete_task(callback: CallbackQuery, state: FSMContext, user=None):
    """Начать процесс отметки задачи как невыполненной"""
    await callback.answer()
    
    task_id = int(callback.data.split("_")[3])
    
    async for session in get_session():
        task = await TaskService.get_task_by_id(session, task_id)
        
        if not task or task.manager_id != user.id:
            await callback.message.edit_text(
                "❌ Задача не найдена!",
                reply_markup=get_manager_menu()
            )
            break
        
        await state.update_data(task_id=task_id)
        await state.set_state(ManagerStates.waiting_for_not_completed_reason)
        
        await callback.message.edit_text(
            "❌ Задача не выполнена.\n\n"
            "📝 Пожалуйста, укажите причину, почему задача не выполнена:"
        )
        break


@router.message(ManagerStates.waiting_for_not_completed_reason)
async def process_not_completed_reason(message: Message, state: FSMContext):
    """Обработать причину невыполнения"""
    reason = message.text
    
    if not reason or len(reason.strip()) < 5:
        await message.answer(
            "❌ Причина должна содержать минимум 5 символов. Попробуйте снова:"
        )
        return
    
    await state.update_data(reason=reason)
    await state.set_state(ManagerStates.waiting_for_new_deadline)
    
    await message.answer(
        "📅 Теперь укажите новый дедлайн в формате <b>ДД.ММ.ГГГГ</b> (например, 25.12.2024):\n\n"
        "⚠️ <b>Важно:</b> Дата должна быть в будущем (не сегодня и не в прошлом)!",
        parse_mode="HTML"
    )


@router.message(ManagerStates.waiting_for_new_deadline)
async def process_new_deadline(message: Message, state: FSMContext, user=None):
    """Обработать новый дедлайн"""
    date_str = message.text.strip()
    
    date_pattern = r"^\d{2}\.\d{2}\.\d{4}$"
    if not re.match(date_pattern, date_str):
        await message.answer(
            "❌ Неверный формат даты! Используйте формат <b>ДД.ММ.ГГГГ</b> (например, 25.12.2024)",
            parse_mode="HTML"
        )
        return
    
    try:
        new_deadline = datetime.strptime(date_str, "%d.%m.%Y")
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        new_deadline = new_deadline.replace(hour=23, minute=59, second=59)
        
        if new_deadline.date() <= today.date():
            await message.answer(
                "❌ Дата должна быть в будущем (не сегодня и не в прошлом)! Попробуйте снова:"
            )
            return
        
        data = await state.get_data()
        task_id = data.get("task_id")
        reason = data.get("reason")
        
        async for session in get_session():
            task = await TaskService.update_task_deadline(
                session, task_id, new_deadline, reason
            )
            
            if task:
                deadline_str = new_deadline.strftime("%d.%m.%Y")
                await message.answer(
                    f"✅ Дедлайн обновлён!\n\n"
                    f"📅 Новый дедлайн: {deadline_str}\n"
                    f"📝 Причина: {reason}\n\n"
                    f"Задача снова активна.",
                    reply_markup=get_manager_menu()
                )
            else:
                await message.answer(
                    "❌ Ошибка при обновлении дедлайна!",
                    reply_markup=get_manager_menu()
                )
            break
        
        await state.clear()
        
    except ValueError:
        await message.answer(
            "❌ Неверная дата! Используйте формат <b>ДД.ММ.ГГГГ</b> (например, 25.12.2024)",
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("tasks_page_"))
async def tasks_pagination(callback: CallbackQuery, user=None):
    """Пагинация задач"""
    await callback.answer()
    
    page = int(callback.data.split("_")[2])
    
    async for session in get_session():
        tasks = await TaskService.get_active_tasks_by_manager(session, user.id)
        
        if not tasks:
            await callback.message.edit_text(
                "✅ У вас нет активных задач!",
                reply_markup=get_manager_menu()
            )
        else:
            text = f"📋 <b>Ваши активные задачи ({len(tasks)}):</b>\n\n"
            start = page * 10
            for i, task in enumerate(tasks[start:start+10], start+1):
                deadline_str = task.deadline.strftime("%d.%m.%Y")
                text += f"{i}. {task.text[:50]}... (до {deadline_str})\n"
            
            await callback.message.edit_text(
                text,
                reply_markup=get_tasks_keyboard(tasks, page=page),
                parse_mode="HTML"
            )
        break

