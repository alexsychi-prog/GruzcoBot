from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    waiting_for_manager_selection = State()
    waiting_for_task_text = State()
    waiting_for_task_deadline = State()

