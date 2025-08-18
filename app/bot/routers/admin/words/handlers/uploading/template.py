import sqlite3
from xlsxwriter.workbook import Workbook
import os


workbook1 = Workbook('output_keyword.xlsx')
workbook2 = Workbook('output_stopword.xlsx')
worksheet1 = workbook1.add_worksheet()
worksheet2 = workbook2.add_worksheet()

db_path = os.path.normpath(os.path.join(
    os.path.dirname(__file__),
    '..',
    '..',
    '..',
    '..',
    '..',
    '..',
    '..',
    'database.db'
))

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

def generate_excel_keyword():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    select_keyword = c.execute("SELECT title FROM word WHERE word_type = 'keyword'")
    write_excel(worksheet1, workbook1, select_keyword, 'Ключ-слово')
    workbook1.close()
    conn.close()

def generate_excel_stopword():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    select_stopword = c.execute("SELECT title FROM word WHERE word_type = 'stopword'")
    write_excel(worksheet2, workbook2, select_stopword, 'Стоп-слово')
    workbook2.close()
    conn.close()