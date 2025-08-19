from xlsxwriter.workbook import Workbook
from xlsxwriter.worksheet import Worksheet
from typing import Iterator
from app.database.repo.Word import WordRepo
from app.bot.routers.admin.words.Markup import Markup
from app.enums import WordType
from aiogram.types.input_file import FSInputFile
from aiogram import types


def write_excel(worksheet: Worksheet, workbook: Workbook, value: Iterator[tuple[str]], name_column: str) -> None:
    border_format = workbook.add_format({
        'border': 2,
        'align': 'left',
        'valign': 'vcenter'
    })
    header_format = workbook.add_format({
        'bold': True,
        'border': 2,
        'bg_color': '#D7E4BC',
        'align': 'center'
    })

    if name_column == 'keyword':
        name = 'Ключ-слова'
    else:
        name = 'Стоп-слова'

    worksheet.write(0, 0, name, header_format)

    max_len = len(name_column)
    for i, row in enumerate(value, start=1):
        worksheet.write(i, 0, row[0], border_format)
        if len(row[0]) > max_len:
            max_len = len(row[0])

    worksheet.set_column(0, 0, max_len * 1.1)


async def generate_excel(word_type: WordType) -> str:
    workbook = Workbook(f'{word_type}.xlsx')
    worksheet = workbook.add_worksheet()

    words = await WordRepo.get_all(word_type)
    words_data = ((word.title,) for word in words)

    write_excel(worksheet, workbook, words_data, f'{word_type}')
    workbook.close()
    return f'{word_type}.xlsx'


async def _process_word_type_upload(cb: types.CallbackQuery, word_type: WordType) -> None:
    config = {
        WordType.keyword: {
            "filename": "Список_ключ_слов.xlsx",
            "message": "<b>Перешли в меню ключ-слов</b> 🔑\n\n📄 Файл Excel отправлен!"
        },
        WordType.stopword: {
            "filename": "Список_стоп_слов.xlsx",
            "message": "<b>🛑 Перешли в меню стоп-слов</b>\n\n📄 Файл Excel отправлен!"
        }
    }

    excel_path = await generate_excel(word_type)
    excel_file = FSInputFile(excel_path, filename=config[word_type]["filename"])

    await cb.message.answer_document(document=excel_file)

    await cb.message.edit_text(
        config[word_type]["message"],
        reply_markup=Markup.open_menu(word_type)
    )
