from aiogram import types, F
from aiogram.fsm.context import FSMContext
from app.bot.routers.admin import admin_router
from app.bot.callback_data import chats_uploading_cb
from .template import generate_excel
from aiogram.types.input_file import FSInputFile


@admin_router.callback_query(F.data == chats_uploading_cb)
async def send_uploading_file_chats(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(None)

    await cb.answer("Файл готов!")

    file_name = 'Список чатов.xlsx'
    excel_path = await generate_excel()
    excel_file = FSInputFile(excel_path, filename=file_name)

    await cb.message.answer_document(document=excel_file)
