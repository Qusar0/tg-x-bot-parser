from xlsxwriter.workbook import Workbook
from xlsxwriter.worksheet import Worksheet
from collections.abc import Iterator
from app.database.repo.Chat import ChatRepo


def write_excel(
    worksheet: Worksheet,
    workbook: Workbook,
    value: Iterator[tuple[str]],
    name_column: str,
    num_column: int
) -> None:
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

    worksheet.write(0, num_column, name_column, header_format)

    max_len = len(name_column)
    for i, row in enumerate(value, start=1):
        if not row[0]:
            row = ['НЕТ ССЫЛКИ']
        if len(row[0]) > max_len:
            max_len = len(row[0])
        worksheet.write(i, num_column, row[0], border_format)

    worksheet.set_column(0, 1, max_len * 1.1)


async def generate_excel() -> str:
    workbook = Workbook('channel.xlsx')
    worksheet = workbook.add_worksheet()

    chats = await ChatRepo.get_all()
    chats_data = ((chat.title,) for chat in chats)

    entity_data = ((entities.entity,) for entities in chats)

    write_excel(worksheet, workbook, chats_data, 'Чаты', 0)
    write_excel(worksheet, workbook, entity_data, 'Ссылка', 1)
    workbook.close()
    return 'channel.xlsx'
