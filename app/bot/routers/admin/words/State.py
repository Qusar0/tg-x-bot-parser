from aiogram.fsm.state import StatesGroup, State


class WordState(StatesGroup):
    add_word = State()
    delete_word = State()
    upload_excel = State()
