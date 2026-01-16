from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from datetime import datetime
from pytz import timezone
from bot.keyboards.admin_keyboards import get_admin_menu, get_manager_list_keyboard
from bot.services.user_service import UserService
from bot.services.task_service import TaskService
from bot.services.file_service import FileService
from bot.services.analytics_service import AnalyticsService
from bot.database.database import get_session
from bot.database.models import GroupAnalytics, User
from bot.states.admin_states import AdminStates
from sqlalchemy import select
import logging
import re

# Белорусское время (UTC+3)
BELARUS_TZ = timezone('Europe/Minsk')

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data == "admin_add_task")
async def start_add_task(callback: CallbackQuery, state: FSMContext):
    """Начать процесс добавления задачи"""
    await callback.answer()
    
    async for session in get_session():
        managers = await UserService.get_all_managers(session)
        
        if not managers:
            await callback.message.edit_text(
                "❌ Нет доступных менеджеров!",
                reply_markup=get_admin_menu()
            )
            break
        
        await state.set_state(AdminStates.waiting_for_manager_selection)
        await callback.message.edit_text(
            "👤 Выберите менеджера для назначения задачи:",
            reply_markup=get_manager_list_keyboard(managers)
        )
        break


@router.callback_query(F.data.startswith("select_manager_"))
async def select_manager(callback: CallbackQuery, state: FSMContext):
    """Выбрать менеджера"""
    await callback.answer()
    
    manager_id = int(callback.data.split("_")[2])
    await state.update_data(manager_id=manager_id)
    await state.set_state(AdminStates.waiting_for_task_text)
    
    await callback.message.edit_text(
        "📝 Введите текст задачи:"
    )


@router.message(AdminStates.waiting_for_task_text)
async def process_task_text(message: Message, state: FSMContext):
    """Обработать текст задачи"""
    task_text = message.text.strip()
    
    if not task_text or len(task_text) < 3:
        await message.answer("❌ Текст задачи должен содержать минимум 3 символа. Попробуйте снова:")
        return
    
    await state.update_data(task_text=task_text)
    await state.set_state(AdminStates.waiting_for_task_deadline)
    
    await message.answer(
        "📅 Введите дедлайн в формате <b>ДД.ММ.ГГГГ</b> (например, 25.12.2024):\n\n"
        "⚠️ <b>Важно:</b> Дата должна быть в будущем!",
        parse_mode="HTML"
    )


@router.message(AdminStates.waiting_for_task_deadline)
async def process_task_deadline(message: Message, state: FSMContext):
    """Обработать дедлайн задачи"""
    date_str = message.text.strip()
    
    date_pattern = r"^\d{2}\.\d{2}\.\d{4}$"
    if not re.match(date_pattern, date_str):
        await message.answer(
            "❌ Неверный формат даты! Используйте формат <b>ДД.ММ.ГГГГ</b> (например, 25.12.2024)",
            parse_mode="HTML"
        )
        return
    
    try:
        deadline = datetime.strptime(date_str, "%d.%m.%Y")
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        deadline = deadline.replace(hour=23, minute=59, second=59)
        
        if deadline.date() <= today.date():
            await message.answer(
                "❌ Дата должна быть в будущем! Попробуйте снова:"
            )
            return
        
        data = await state.get_data()
        manager_id = data.get("manager_id")
        task_text = data.get("task_text")
        
        async for session in get_session():
            task = await TaskService.create_task(session, manager_id, task_text, deadline)
            
            result = await session.execute(select(User).where(User.id == manager_id))
            manager = result.scalar_one_or_none()
            
            manager_name = manager.first_name if manager else "N/A"
            
            await message.answer(
                f"✅ Задача успешно создана!\n\n"
                f"📌 Текст: {task_text}\n"
                f"📅 Дедлайн: {deadline.strftime('%d.%m.%Y')}\n"
                f"👤 Менеджер: {manager_name}",
                reply_markup=get_admin_menu()
            )
            break
        
        await state.clear()
        
    except ValueError:
        await message.answer(
            "❌ Неверная дата! Используйте формат <b>ДД.ММ.ГГГГ</b> (например, 25.12.2024)",
            parse_mode="HTML"
        )


@router.callback_query(F.data == "admin_cancel")
async def cancel_admin_action(callback: CallbackQuery, state: FSMContext):
    """Отменить действие администратора"""
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(
        "❌ Действие отменено.",
        reply_markup=get_admin_menu()
    )


@router.callback_query(F.data == "admin_all_tasks")
async def show_all_tasks(callback: CallbackQuery):
    """Показать все задачи"""
    await callback.answer()
    
    try:
        async for session in get_session():
            tasks = await TaskService.get_all_tasks(session)
            
            if not tasks:
                await callback.message.edit_text(
                    "📋 Нет задач в системе.",
                    reply_markup=get_admin_menu()
                )
                break
            
            text = f"📋 <b>Все задачи ({len(tasks)}):</b>\n\n"
            
            for task in tasks[:50]:
                status_emoji = {
                    "active": "🟡",
                    "completed": "✅",
                    "not_completed": "❌"
                }
                emoji = status_emoji.get(task.status, "⚪")
                
                # Безопасное получение имени менеджера
                if task.manager:
                    manager_name = task.manager.first_name or task.manager.username or f"ID: {task.manager.telegram_id}"
                else:
                    manager_name = "N/A"
                
                deadline_str = task.deadline.strftime("%d.%m.%Y")
                task_text = task.text[:60] + "..." if len(task.text) > 60 else task.text
                
                text += (
                    f"{emoji} <b>#{task.id}</b> | {manager_name}\n"
                    f"   {task_text}\n"
                    f"   📅 {deadline_str} | Статус: {task.status}\n\n"
                )
            
            if len(tasks) > 50:
                text += f"\n... и ещё {len(tasks) - 50} задач"
            
            await callback.message.edit_text(
                text,
                reply_markup=get_admin_menu(),
                parse_mode="HTML"
            )
            break
    except Exception as e:
        logger.error(f"Error in show_all_tasks: {e}", exc_info=True)
        await callback.message.edit_text(
            "❌ Произошла ошибка при получении списка задач.",
            reply_markup=get_admin_menu()
        )


@router.callback_query(F.data == "admin_all_employees")
async def show_all_employees(callback: CallbackQuery):
    """Показать всех сотрудников с детальной статистикой"""
    await callback.answer()
    
    try:
        async for session in get_session():
            stats = await TaskService.get_detailed_manager_statistics(session)
            
            if not stats:
                await callback.message.edit_text(
                    "👥 <b>ВСЕ СОТРУДНИКИ</b>\n\n"
                    "Нет зарегистрированных сотрудников.",
                    reply_markup=get_admin_menu(),
                    parse_mode="HTML"
                )
                break
            
            text = f"👥 <b>ВСЕ СОТРУДНИКИ ({len(stats)})</b>\n\n"
            
            for stat in stats:
                text += (
                    f"<b>{stat['name']}</b>\n"
                    f"   ✅ Выполнено: {stat['completed']}\n"
                    f"   ❌ Не выполнено: {stat['not_completed']}\n"
                    f"   🟡 Активных: {stat['active']}\n"
                    f"   📊 Процент выполнения: {stat['percentage']}%\n"
                    f"   📋 Всего задач: {stat['total']}\n\n"
                )
            
            await callback.message.edit_text(
                text,
                reply_markup=get_admin_menu(),
                parse_mode="HTML"
            )
            break
    except Exception as e:
        logger.error(f"Error in show_all_employees: {e}", exc_info=True)
        await callback.message.edit_text(
            "❌ Произошла ошибка при получении списка сотрудников.",
            reply_markup=get_admin_menu()
        )


@router.callback_query(F.data == "admin_rating")
async def show_rating(callback: CallbackQuery):
    """Показать рейтинг менеджеров"""
    await callback.answer()
    
    try:
        async for session in get_session():
            stats = await TaskService.get_manager_statistics(session)
            
            if not stats:
                await callback.message.edit_text(
                    "📊 Нет данных для рейтинга.\n\nДобавьте задачи менеджерам, чтобы увидеть статистику.",
                    reply_markup=get_admin_menu()
                )
                break
            
            text = "🏆 <b>РЕЙТИНГ МЕНЕДЖЕРОВ</b>\n\n"
            
            for i, stat in enumerate(stats, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                
                text += (
                    f"{medal} <b>{stat['name']}</b>\n"
                    f"   ✅ Выполнено: {stat['completed']}\n"
                    f"   ❌ Не выполнено: {stat['not_completed']}\n"
                    f"   📊 Процент выполнения: {stat['percentage']}%\n"
                    f"   📋 Всего задач: {stat['total']}\n\n"
                )
            
            await callback.message.edit_text(
                text,
                reply_markup=get_admin_menu(),
                parse_mode="HTML"
            )
            break
    except Exception as e:
        logger.error(f"Error in show_rating: {e}", exc_info=True)
        await callback.message.edit_text(
            "❌ Произошла ошибка при получении рейтинга.",
            reply_markup=get_admin_menu()
        )


@router.callback_query(F.data == "admin_cleanup")
async def cleanup_completed_tasks(callback: CallbackQuery):
    """Очистить выполненные задачи"""
    await callback.answer()
    
    try:
        async for session in get_session():
            # Получаем задачи с загруженным менеджером для сохранения в файл
            old_tasks = await TaskService.get_completed_tasks_older_than_with_manager(session, days=7)
            
            # Отладочная информация
            logger.info(f"Found {len(old_tasks)} completed tasks older than 7 days")
            
            if not old_tasks:
                # Проверяем, есть ли вообще выполненные задачи
                from sqlalchemy import select
                from bot.database.models import Task
                all_completed = await session.execute(
                    select(Task).where(Task.status == "completed")
                )
                all_completed_tasks = list(all_completed.scalars().all())
                
                if all_completed_tasks:
                    # Показываем информацию о выполненных задачах
                    oldest_task = min(all_completed_tasks, key=lambda t: t.completed_at if t.completed_at else datetime.utcnow())
                    days_old = (datetime.utcnow() - (oldest_task.completed_at or datetime.utcnow())).days
                    
                    await callback.message.edit_text(
                        f"✅ Нет выполненных задач старше 7 дней для очистки.\n\n"
                        f"📊 Всего выполненных задач: {len(all_completed_tasks)}\n"
                        f"📅 Самая старая выполнена {days_old} дней назад",
                        reply_markup=get_admin_menu()
                    )
                else:
                    await callback.message.edit_text(
                        "✅ Нет выполненных задач старше 7 дней для очистки.\n\n"
                        "📊 Выполненных задач в системе нет.",
                        reply_markup=get_admin_menu()
                    )
                break
            
            # Сохраняем задачи в файл ПЕРЕД удалением
            filepath = await FileService.save_completed_tasks_to_file(old_tasks)
            
            task_ids = [task.id for task in old_tasks]
            deleted_count = await TaskService.delete_tasks(session, task_ids)
            
            # Обновляем лог последней очистки
            from bot.database.models import CleanupLog
            from sqlalchemy import select
            
            result = await session.execute(select(CleanupLog).order_by(CleanupLog.id.desc()).limit(1))
            cleanup_log = result.scalar_one_or_none()
            
            if cleanup_log:
                cleanup_log.last_cleanup_date = datetime.utcnow()
                cleanup_log.tasks_deleted = deleted_count
                cleanup_log.cleanup_type = "manual"
            else:
                cleanup_log = CleanupLog(
                    last_cleanup_date=datetime.utcnow(),
                    tasks_deleted=deleted_count,
                    cleanup_type="manual"
                )
                session.add(cleanup_log)
            
            await session.commit()
            
            await callback.message.edit_text(
                f"✅ Очистка завершена!\n\n"
                f"🗑️ Удалено задач: {deleted_count}\n\n"
                f"💾 Данные сохранены в файл:\n"
                f"<code>{filepath}</code>",
                reply_markup=get_admin_menu(),
                parse_mode="HTML"
            )
            break
    except Exception as e:
        logger.error(f"Error in cleanup_completed_tasks: {e}", exc_info=True)
        await callback.message.edit_text(
            "❌ Произошла ошибка при очистке задач.",
            reply_markup=get_admin_menu()
        )


@router.callback_query(F.data == "admin_group_analysis")
async def show_group_analysis_menu(callback: CallbackQuery, bot):
    """Показать меню анализа групп"""
    await callback.answer()
    
    async for session in get_session():
        result = await session.execute(select(GroupAnalytics))
        groups = result.scalars().all()
        
        if not groups:
            text = (
                "📊 <b>АНАЛИЗ TELEGRAM-ГРУПП</b>\n\n"
                "Добавьте бота в группу для начала анализа.\n\n"
                "Для получения аналитики добавьте бота в группу с правами администратора."
            )
        else:
            text = "📊 <b>АНАЛИЗ TELEGRAM-ГРУПП</b>\n\n"
            for group in groups:
                # Обновляем количество участников
                try:
                    member_count = await bot.get_chat_member_count(group.group_id)
                    if group.total_members != member_count:
                        group.total_members = member_count
                        await session.commit()
                except Exception as e:
                    logger.error(f"Error updating member count for group {group.group_id}: {e}")
                
                # Получаем список вышедших и исключенных участников
                left_members = await AnalyticsService.get_left_members(session, group.id)
                
                # Разделяем на вышедших и исключенных
                left_list = [m for m in left_members if m.status == "left"]
                kicked_list = [m for m in left_members if m.status == "kicked"]
                
                # Формируем username для вышедших
                left_usernames = []
                for m in left_list[:10]:
                    if m.username:
                        left_usernames.append(f"@{m.username}")
                    elif m.first_name:
                        left_usernames.append(f"{m.first_name} (ID: {m.telegram_id})")
                    else:
                        left_usernames.append(f"ID: {m.telegram_id}")
                
                # Формируем username для исключенных
                kicked_usernames = []
                for m in kicked_list[:10]:
                    if m.username:
                        kicked_usernames.append(f"@{m.username}")
                    elif m.first_name:
                        kicked_usernames.append(f"{m.first_name} (ID: {m.telegram_id})")
                    else:
                        kicked_usernames.append(f"ID: {m.telegram_id}")
                
                text += (
                    f"<b>{group.group_title or f'Группа {group.group_id}'}</b>\n"
                    f"👥 Всего участников: {group.total_members}\n"
                    f"🚪 Вышли: {group.left_members}\n"
                    f"👢 Исключены: {group.kicked_members}\n"
                )
                
                # Показываем вышедших
                if left_usernames:
                    text += f"\n🚪 <b>Вышедшие участники:</b>\n"
                    text += ", ".join(left_usernames[:5])
                    if len(left_usernames) > 5:
                        text += f" и ещё {len(left_usernames) - 5}"
                    text += "\n"
                
                # Показываем исключенных
                if kicked_usernames:
                    text += f"\n👢 <b>Исключенные участники:</b>\n"
                    text += ", ".join(kicked_usernames[:5])
                    if len(kicked_usernames) > 5:
                        text += f" и ещё {len(kicked_usernames) - 5}"
                    text += "\n"
                
                # Конвертируем UTC время в белорусское время
                if group.last_updated:
                    # Если last_updated naive (без timezone), считаем что это UTC
                    if group.last_updated.tzinfo is None:
                        utc_time = timezone('UTC').localize(group.last_updated)
                    else:
                        utc_time = group.last_updated
                    belarus_time = utc_time.astimezone(BELARUS_TZ)
                    time_str = belarus_time.strftime('%d.%m.%Y %H:%M')
                else:
                    time_str = "N/A"
                text += f"\n🕐 Обновлено: {time_str} (МСК+1)\n\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_admin_menu(),
            parse_mode="HTML"
        )
        break

