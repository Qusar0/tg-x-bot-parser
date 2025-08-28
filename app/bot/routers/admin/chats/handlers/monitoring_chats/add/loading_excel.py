import pandas as pd
import io
from typing import List, Tuple
import logging


logger = logging.getLogger(__name__)


class ExcelChatParser:
    @staticmethod
    def parse_excel_file(file_content: bytes) -> Tuple[List[dict], List[str]]:
        excel_file = io.BytesIO(file_content)

        df = pd.read_excel(excel_file, engine='openpyxl')

        df = df.dropna(subset=['Название чата', 'Ссылка'])

        chats = []
        errors = []

        for index, row in df.iterrows():
            chat_name = str(row['Название чата']).strip()
            chat_link = str(row['Ссылка']).strip()

            validation_errors = ExcelChatParser._validate_chat_data(chat_name, chat_link, index + 1)
            errors.extend(validation_errors)

            normalized_link = ExcelChatParser._normalize_chat_link(chat_link)

            chats.append({
                'name': chat_name,
                'link': normalized_link,
                'original_link': chat_link,
                'row_number': index + 1
            })

        logger.debug(f"Обработана строка {index + 1}: {chat_name}")
        return chats, errors

    @staticmethod
    def _validate_chat_data(chat_name: str, chat_link: str, row_number: int) -> List[str]:
        errors = []

        if not chat_name or chat_name == 'nan':
            errors.append(f"Строка {row_number}: Пустое название чата")

        if not chat_link or chat_link == 'nan':
            errors.append(f"Строка {row_number}: Пустая ссылка")

        if len(chat_name) > 255:
            errors.append(f"Строка {row_number}: Название чата слишком длинное (максимум 255 символов)")

        if chat_link and not ExcelChatParser._is_valid_chat_link(chat_link):
            errors.append(f"Строка {row_number}: Некорректный формат ссылки '{chat_link}'")

        return errors

    @staticmethod
    def _is_valid_chat_link(link: str) -> bool:
        """Проверяет корректность формата ссылки на чат"""
        link = link.strip()

        valid_patterns = [
            link.startswith('@'),
            link.startswith('https://t.me/'),
            link.startswith('http://t.me/'),
            link.startswith('t.me/'),
            link.isdigit() and len(link) > 5,  # Числовой ID
        ]

        return any(valid_patterns)

    @staticmethod
    def _normalize_chat_link(link: str) -> str:
        """Нормализует ссылку на чат к стандартному формату"""
        link = link.strip()

        if not link.startswith(('@', 'https://', 'http://')) and not link.isdigit():
            if '/' in link and link.startswith('t.me/'):
                link = 'https://' + link
            elif not link.startswith('@'):
                link = '@' + link

        return link

    @staticmethod
    def create_template_excel() -> bytes:
        data = {
            'Название чата': [
                'Пример чата 1',
                'Пример чата 2',
                'Пример чата 3',
                'Пример чата 4'
            ],
            'Ссылка': [
                '@username',
                'https://t.me/username',
                'https://t.me/+abcd12345',
                'https://t.me/AAAAabcd12345'
            ]
        }

        df = pd.DataFrame(data)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Чаты')

        output.seek(0)
        return output.getvalue()
