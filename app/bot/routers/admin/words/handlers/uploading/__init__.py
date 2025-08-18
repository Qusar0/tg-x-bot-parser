from aiogram import types
from aiogram.types.input_file import FSInputFile
from aiogram.fsm.context import FSMContext
from app.bot.routers.admin import admin_router
from app.bot.callback_data import WordUploadingCb
from .template import generate_excel
from app.bot.routers.admin.words.Markup import Markup
from app.enums import WordType



@admin_router.callback_query(WordUploadingCb.filter())
async def send_uploading_file(cb: types.CallbackQuery, callback_data: WordUploadingCb, state: FSMContext):
    await state.set_state(None)
    word_type = callback_data.word_type

    await cb.answer("Файл готов!")
    if word_type == WordType.keyword:
        excel_path = generate_excel(WordType.keyword)
        excel_file = FSInputFile(excel_path, filename="Список_ключ_слов.xlsx")

        await cb.message.answer_document(document=excel_file)

        await cb.message.edit_text(
            "<b>Перешли в меню ключ-слов</b> 🔑\n\n📄 Файл Excel отправлен!",
            reply_markup=Markup.open_menu(WordType.keyword)
        )
    else:
        excel_path = generate_excel(WordType.stopword)
        excel_file = FSInputFile(excel_path, filename="Список_стоп_слов.xlsx")

        await cb.message.answer_document(document=excel_file)

        await cb.message.edit_text(
            "<b>🛑 Перешли в меню стоп-слов</b>\n\n📄 Файл Excel отправлен!",
            reply_markup=Markup.open_menu(WordType.stopword)
        )