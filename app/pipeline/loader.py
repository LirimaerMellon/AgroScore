import pandas as pd
import logging
from typing import List, Set

from app.config import REQUIRED_COLUMNS


class DataLoader:
    """
    DataLoader — сервис для загрузки и первичной валидации данных.

    Принципы:
    - Dependency Injection (логгер, конфиг)
    - Отсутствие статических методов
    - Расширяемость
    - Тестируемость
    """

    def __init__(
        self,
        required_columns: List[str] = REQUIRED_COLUMNS,
        logger: logging.Logger = None
    ):
        # Конфигурация обязательных колонок
        self.required_columns: Set[str] = set(required_columns)

        # Логгер (можно подменять в тестах)
        self.logger = logger or logging.getLogger(__name__)


    def load_data(self, file_path: str) -> pd.DataFrame:
        """
        Загружает данные из файла (csv / excel) и возвращает DataFrame.
        """

        # Проверка расширения файла
        if not file_path.endswith((".xlsx", ".xls", ".csv")):
            raise ValueError(
                "Файл должен иметь допустимое расширение: .xlsx, .xls или .csv"
            )

        # Загрузка данных
        if file_path.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(
                file_path,
                sep=None,
                engine="python",
                encoding="utf-8"
            )

        # Проверка на пустые данные
        if df.empty:
            raise ValueError("Файл загружен, но DataFrame пустой")

        # Нормализация колонок
        df.columns = df.columns.str.strip()

        # Логирование
        self.logger.info(f"Загружено {len(df):,} строк")
        self.logger.info(f"Столбцы: {df.columns.tolist()}")

        return df

    def validate_columns(self, df: pd.DataFrame) -> None:
        """
        Проверяет наличие обязательных колонок.
        """

        df_columns = {col.strip() for col in df.columns}

        missing = list(self.required_columns - df_columns)

        if missing:
            self.logger.warning(f"Не найдено столбцов: {missing}")
            raise ValueError(f"Не найдены обязательные столбцы: {missing}")

        self.logger.info("Все необходимые столбцы присутствуют")