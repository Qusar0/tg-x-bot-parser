from aiogram.fsm.state import StatesGroup, State


class ChatsState(StatesGroup):
    add = State()
    delete = State()

    add_central_chat = State()
    add_excel = State()

    set_winrate= State()
    set_x_winrate= State()
