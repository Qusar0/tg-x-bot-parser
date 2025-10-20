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
    # Определяем название файла
    is_keyword = word_type in [WordType.tg_keyword, WordType.x_keyword]
    is_stopword = word_type in [WordType.tg_stopword, WordType.x_stopword]
    is_filter_word = word_type in [WordType.tg_filter_word, WordType.x_filter_word]
    
    platform = "TG" if word_type.value.startswith("tg_") else "X"
    
    if is_keyword:
        filename = f'Список_ключ_слов_{platform}.xlsx'
    elif is_stopword:
        filename = f'Список_стоп_слов_{platform}.xlsx'
    elif is_filter_word:
        filename = f'Список_фильтр_слов_{platform}.xlsx'

    excel_path = await generate_excel(word_type)
    excel_file = FSInputFile(excel_path, filename=filename)

    await cb.message.answer_document(document=excel_file)
