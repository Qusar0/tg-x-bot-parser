from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.types.input_file import FSInputFile, BufferedInputFile
from app.bot.routers.admin import admin_router
from app.bot.callback_data import WordExcelLoadCb, ChooseChatForExcelCb
from app.bot.routers.admin.words.State import WordState
from app.bot.routers.admin.words.Markup import Markup
from app.database.repo.Word import WordRepo
from .loading_excel_word import ExcelWordParser
from app.enums import WordType


@admin_router.callback_query(WordExcelLoadCb.filter())
async def excel_upload_handler(cb: types.CallbackQuery, callback_data: WordExcelLoadCb, state: FSMContext):
    await state.update_data(word_type=callback_data.word_type)

    word_type_name = "ключевых слов" if callback_data.word_type.value == "keyword" else "стоп-слов"

    await cb.message.edit_text(
        f"📗 <b>Загрузка {word_type_name} из Excel</b>\n\n"
        f"💬 В какой чат добавить {word_type_name}?",
        reply_markup=Markup.choose_central_chat_for_excel(callback_data.word_type)
    )
    await cb.answer()


@admin_router.callback_query(ChooseChatForExcelCb.filter())
async def choose_chat_for_excel(cb: types.CallbackQuery, callback_data: ChooseChatForExcelCb, state: FSMContext):
    await state.update_data(central_chat_id=callback_data.chat_id)
    await state.set_state(WordState.upload_excel)

    word_type = callback_data.word_type
    word_type_name = "ключевых слов" if word_type.value == "keyword" else "стоп-слов"

    template_data = ExcelWordParser.create_template_excel(word_type)
    template_file = BufferedInputFile(template_data, filename=f"template_{word_type.value}.xlsx")

    await cb.message.answer_document(
        document=template_file,
        caption=f"📗 <b>Загрузка {word_type_name} из Excel</b>\n\n"
                f"📄 Отправьте Excel файл со списком {word_type_name}.\n\n"
                f"📋 <b>Требования к файлу:</b>\n"
                f"• Формат: .xlsx или .xls\n"
                f"• Столбец должен называться: <code>{word_type.value}</code>\n"
                f"• Каждое слово в отдельной строке\n"
                f"• Не должно быть пустых строк\n\n"
                f"📥 <b>Выше отправлен шаблон файла для примера</b>\n"
                f"Скачайте его, заполните своими словами и отправьте обратно!",
        reply_markup=Markup.cancel_action()
    )

    await cb.message.delete()
    await cb.answer()


@admin_router.message(F.document, WordState.upload_excel)
async def process_excel_upload(message: types.Message, state: FSMContext):
    data = await state.get_data()
    word_type_str = data.get('word_type')

    word_type = WordType(word_type_str)

    document = message.document

    await message.answer("⏳ <b>Обрабатываю Excel файл...</b>")

    file = await message.bot.get_file(document.file_id)
    file_content = await message.bot.download_file(file.file_path)

    words = ExcelWordParser.parse_excel_file(file_content.getvalue(), word_type)

    central_chat_id = data.get('central_chat_id')

    if not central_chat_id:
        await message.answer(
            "❌ <b>Ошибка: чат не выбран!</b>\n\n"
            "Пожалуйста, начните заново.",
            reply_markup=Markup.cancel_action()
        )
        return

    added_words = await WordRepo.add_many(words, word_type, central_chat_id)

    word_type_name = "ключевых слов" if word_type.value == "keyword" else "стоп-слов"

    success_message = (
        f"✅ <b>Загрузка {word_type_name} завершена!</b>\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"• Всего в файле: {len(words)}\n"
        f"• Добавлено новых: {len(added_words)}\n"
        f"• Пропущено дубликатов: {len(words) - len(added_words)}"
    )

    await message.answer(
        success_message,
        reply_markup=Markup.open_menu(word_type)
    )

    await state.clear()


@admin_router.callback_query(F.data == "cancel_action")
async def cancel_excel_upload(cb: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()

    if current_state == WordState.upload_excel.state:
        data = await state.get_data()
        word_type = data.get('word_type')

        await state.clear()

        if word_type:
            word_type_enum = WordType(word_type)
            await cb.message.delete()
            await cb.message.answer(
                f"❌ <b>Загрузка отменена</b>",
                reply_markup=Markup.open_menu(word_type_enum)
            )
        else:
            await cb.message.delete()
            await cb.message.answer("❌ <b>Загрузка отменена</b>")
        
        await cb.answer()
