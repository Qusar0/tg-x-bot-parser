from aiogram import types
from aiogram.fsm.context import FSMContext
from app.bot.routers.admin import admin_router
from app.bot.callback_data import WordUploadingCb
from .template import _process_word_type_upload


@admin_router.callback_query(WordUploadingCb.filter())
async def send_uploading_file(cb: types.CallbackQuery, callback_data: WordUploadingCb, state: FSMContext):
    await state.set_state(None)
    word_type = callback_data.word_type

    await cb.answer("Файл готов!")

    await _process_word_type_upload(cb, word_type)
