from aiogram.fsm.state import State, StatesGroup


class ManagerStates(StatesGroup):
    waiting_for_not_completed_reason = State()
    waiting_for_new_deadline = State()

