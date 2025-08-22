from xlsxwriter.workbook import Workbook
from xlsxwriter.worksheet import Worksheet
from collections.abc import Iterator
from app.database.repo.Word import WordRepo
from app.enums import WordType
from aiogram.types.input_file import FSInputFile
from aiogram import types
import tempfile


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

    max_len = len(name)
    for i, row in enumerate(value, start=1):
        worksheet.write(i, 0, row[0], border_format)
        if len(row[0]) > max_len:
            max_len = len(row[0])

    worksheet.set_column(0, 0, max_len * 1.1)


async def generate_excel(word_type: WordType) -> str:
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
        temp_filename = tmp_file.name

    workbook = Workbook(temp_filename)
    worksheet = workbook.add_worksheet()

    words = await WordRepo.get_all(word_type)
    words_data = ((word.title,) for word in words)

    write_excel(worksheet, workbook, words_data, f'{word_type}')
    workbook.close()
    return temp_filename


async def _process_word_type_upload(cb: types.CallbackQuery, word_type: WordType) -> None:
    filename = 'Список_ключ_слов.xlsx' if word_type == WordType.keyword else 'Список_стоп_слов.xlsx'

    excel_path = await generate_excel(word_type)
    excel_file = FSInputFile(excel_path, filename=filename)

    await cb.message.answer_document(document=excel_file)
