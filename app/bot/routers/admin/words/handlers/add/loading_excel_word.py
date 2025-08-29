import pandas as pd
import io
from typing import List
from app.enums import WordType


class ExcelWordParser:
    @staticmethod
    def parse_excel_file(file_content: bytes, word_type: WordType) -> List[str]:
        excel_file = io.BytesIO(file_content)

        df = pd.read_excel(excel_file, engine='openpyxl')

        column_name = 'Ключ-слова' if word_type.value == 'keyword' else 'Стоп-слова'

        if column_name not in df.columns:
            raise ValueError(f"Столбец '{column_name}' не найден в Excel файле")

        df = df.dropna(subset=[column_name])

        words = []

        for _, row in df.iterrows():
            word = str(row[column_name]).strip()
            if word and word != 'nan':
                words.append(word)

        return words

    @staticmethod
    def create_template_excel(word_type: WordType) -> bytes:
        column_name = 'Ключ-слова' if word_type.value == 'keyword' else 'Стоп-слова'

        data = {
            column_name: [
                'пример слова 1',
                'пример слова 2',
                'пример слова 3'
            ],
        }

        df = pd.DataFrame(data)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Слова')

        output.seek(0)
        return output.getvalue()
