from aiogram.fsm.state import StatesGroup, State


class ChatsState(StatesGroup):
    add = State()
    delete = State()

    add_central_chat = State()
