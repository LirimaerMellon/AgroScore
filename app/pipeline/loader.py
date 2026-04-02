"""
DataLoader — загрузка данных из Excel, CSV и JSON.
Автоматически определяет строку заголовков в Excel.
"""

import io
import pandas as pd
import logging
from typing import List, Set, Optional

from app.config import REQUIRED_COLUMNS


class DataLoader:

    # Маркеры для определения строки заголовков
    HEADER_MARKERS = {
        'Дата поступления', 'Область', 'Номер заявки',
        'Статус заявки', 'Норматив', 'Акимат',
    }

    def __init__(
        self,
        required_columns: Optional[List[str]] = None,
        logger: logging.Logger = None,
    ):
        if required_columns is None:
            required_columns = REQUIRED_COLUMNS
        self.required_columns: Set[str] = set(required_columns)
        self.logger = logger or logging.getLogger(__name__)

    def load_data(self, file_path: str) -> pd.DataFrame:
        """Загружает данные из файла на диске (csv / excel / json)."""
        if file_path.endswith((".xlsx", ".xls")):
            df = self._load_excel(file_path)
        elif file_path.endswith(".csv"):
            df = pd.read_csv(file_path, sep=None, engine="python", encoding="utf-8")
        elif file_path.endswith(".json"):
            df = pd.read_json(file_path, orient="records", encoding="utf-8")
        else:
            raise ValueError("Допустимые форматы: .xlsx, .xls, .csv, .json")

        return self._post_process(df, source=file_path)

    def load_from_buffer(self, buf: io.BytesIO, filename: str) -> pd.DataFrame:
        """Загружает данные из BytesIO-буфера (без записи на диск)."""
        if filename.endswith((".xlsx", ".xls")):
            df = self._load_excel_buffer(buf)
        elif filename.endswith(".csv"):
            df = pd.read_csv(buf, sep=None, engine="python", encoding="utf-8")
        else:
            raise ValueError("Допустимые форматы: .xlsx, .xls, .csv")

        return self._post_process(df, source=filename)

    def _post_process(self, df: pd.DataFrame, source: str) -> pd.DataFrame:
        """Общая постобработка после загрузки."""
        if df.empty:
            raise ValueError("Файл загружен, но DataFrame пустой")

        df.columns = df.columns.str.strip()
        # Убираем полностью пустые колонки
        df = df.dropna(axis=1, how='all')

        self.logger.info(f"Загружено {len(df):,} строк из {source}")
        return df

    def _load_excel(self, file_path: str) -> pd.DataFrame:
        """Загружает Excel с диска с автодетекцией строки заголовков."""
        try:
            probe = pd.read_excel(file_path, header=None, nrows=20)
            header_row = self._find_header_row(probe)
        except Exception:
            header_row = 0

        df = pd.read_excel(file_path, header=header_row, dtype=str)
        # Удаляем Unnamed колонки
        df = df.loc[:, ~df.columns.astype(str).str.startswith('Unnamed')]
        return df

    def _load_excel_buffer(self, buf: io.BytesIO) -> pd.DataFrame:
        """Загружает Excel из BytesIO с автодетекцией строки заголовков."""
        try:
            buf.seek(0)
            probe = pd.read_excel(buf, header=None, nrows=20)
            header_row = self._find_header_row(probe)
        except Exception:
            header_row = 0

        buf.seek(0)
        df = pd.read_excel(buf, header=header_row, dtype=str)
        df = df.loc[:, ~df.columns.astype(str).str.startswith('Unnamed')]
        return df

    def _find_header_row(self, probe: pd.DataFrame) -> int:
        """Ищет строку, содержащую маркерные заголовки."""
        for idx in range(min(20, len(probe))):
            row_values = set()
            for val in probe.iloc[idx]:
                if isinstance(val, str):
                    row_values.add(val.strip())
            matches = row_values & self.HEADER_MARKERS
            if len(matches) >= 3:
                self.logger.info(f"Заголовки обнаружены на строке {idx}")
                return idx
        return 0

    @staticmethod
    def load_from_records(records: list) -> pd.DataFrame:
        """Загружает данные из списка словарей (JSON body)."""
        df = pd.DataFrame(records)
        if df.empty:
            raise ValueError("Переданные данные пусты")
        df.columns = df.columns.str.strip()
        return df

    def validate_columns(self, df: pd.DataFrame) -> None:
        """Проверяет наличие обязательных колонок."""
        if not self.required_columns:
            return
        missing = list(self.required_columns - set(df.columns))
        if missing:
            self.logger.warning(f"Не найдено столбцов: {missing}")
            raise ValueError(f"Не найдены обязательные столбцы: {missing}")

        self.logger.info("Все необходимые столбцы присутствуют")