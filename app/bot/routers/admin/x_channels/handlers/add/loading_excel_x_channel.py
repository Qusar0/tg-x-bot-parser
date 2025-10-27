import pandas as pd
import io
from typing import List, Tuple
from loguru import logger


class ExcelXChannelParser:
    @staticmethod
    def parse_excel_file(file_content: bytes) -> Tuple[List[dict], List[str]]:
        excel_file = io.BytesIO(file_content)

        df = pd.read_excel(excel_file, engine='openpyxl')

        df = df.dropna(subset=['Название канала', 'Ссылка'])

        channels = []
        validation_errors = []

        for index, row in df.iterrows():
            channel_name = str(row['Название канала']).strip()
            channel_link = str(row['Ссылка']).strip()

            errors = ExcelXChannelParser._validate_channel_data(channel_name, channel_link, index + 1)
            validation_errors.extend(errors)

            if not errors:  # Добавляем только если нет ошибок валидации
                normalized_link = ExcelXChannelParser._normalize_channel_link(channel_link)

                channels.append({
                    'name': channel_name,
                    'link': normalized_link,
                    'original_link': channel_link,
                    'row_number': index + 1
                })

        return channels, validation_errors

    @staticmethod
    def _validate_channel_data(channel_name: str, channel_link: str, row_number: int) -> List[str]:
        errors = []

        if not channel_name or channel_name == 'nan':
            errors.append(f"Строка {row_number}: Пустое название канала")

        if not channel_link or channel_link == 'nan':
            errors.append(f"Строка {row_number}: Пустая ссылка")

        if len(channel_name) > 255:
            errors.append(f"Строка {row_number}: Название канала слишком длинное (максимум 255 символов)")

        if channel_link and not ExcelXChannelParser._is_valid_channel_link(channel_link):
            errors.append(f"Строка {row_number}: Некорректный формат ссылки '{channel_link}'")

        if not errors:
            logger.info(f"Успешно обработана строка {row_number}: {channel_name}")

        return errors

    @staticmethod
    def _is_valid_channel_link(link: str) -> bool:
        """Проверяет корректность формата ссылки на X канал"""
        link = link.strip()

        valid_patterns = [
            link.startswith('https://x.com/'),
            link.startswith('https://twitter.com/'),
            link.startswith('http://x.com/'),
            link.startswith('http://twitter.com/'),
            link.startswith('x.com/'),
            link.startswith('twitter.com/'),
            link.startswith('@') and len(link) > 1,  # @username
        ]

        return any(valid_patterns)

    @staticmethod
    def _normalize_channel_link(link: str) -> str:
        """Нормализует ссылку на X канал к стандартному формату"""
        link = link.strip()

        if link.startswith('@'):
            # Если это @username, конвертируем в полную ссылку
            username = link[1:]  # убираем @
            link = f"https://x.com/{username}"
        elif not link.startswith(('https://', 'http://')):
            if link.startswith(('x.com/', 'twitter.com/')):
                link = 'https://' + link
            else:
                # Предполагаем, что это username
                link = f"https://x.com/{link}"

        return link

    @staticmethod
    def create_template_excel() -> bytes:
        data = {
            'Название канала': [
                'SpaceX',
                'Elon Musk',
                'OpenAI',
                'Tesla'
            ],
            'Ссылка': [
                'https://x.com/SpaceX',
                '@elonmusk',
                'https://x.com/OpenAI',
                'x.com/Tesla'
            ]
        }

        df = pd.DataFrame(data)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='X каналы')

        output.seek(0)
        return output.getvalue()

