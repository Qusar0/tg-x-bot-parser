from aiogram.fsm.state import State, StatesGroup


class XChannelStates(StatesGroup):
    waiting_for_manual_input = State()

