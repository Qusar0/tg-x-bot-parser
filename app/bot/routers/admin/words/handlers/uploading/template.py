import sqlite3
from xlsxwriter.workbook import Workbook
from pathlib import Path


db_path = Path(__file__).parents[7] / "database.db"

def write_excel(worksheet, workbook, value, name_column):
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

    worksheet.write(0, 0, name_column, header_format)

    max_len = len(name_column)
    for i, row in enumerate(value, start=1):
        worksheet.write(i, 0, row[0], border_format)
        if len(row[0]) > max_len:
            max_len = len(row[0])

    worksheet.set_column(0, 0, max_len * 1.1)

def generate_excel(word_type):
    workbook1 = Workbook(f'{word_type}.xlsx')
    worksheet1 = workbook1.add_worksheet()

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    select_keyword = c.execute(f"SELECT title FROM word WHERE word_type = '{word_type}'")
    write_excel(worksheet1, workbook1, select_keyword, f'{word_type}')
    workbook1.close()
    conn.close()
    return f'{word_type}.xlsx'