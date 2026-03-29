import pandas as pd
import logging
from typing import Tuple
from app.config import REQUIRED_COLUMNS

logger = logging.getLogger(__name__)


def load_data(file_path: str) -> pd.DataFrame:
    try:
        if not file_path.endswith((".xlsx", ".xls", ".csv")):
            raise ValueError("File must be .xlsx, .xls or .csv")

        # Excel
        if file_path.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file_path, dtype={'application_id': str})

        # CSV
        else:
            df = pd.read_csv(
                file_path,
                sep=';',
                dtype={'application_id': str},
                encoding='utf-8'
            )

        if df.empty:
            raise ValueError("Не удалось загрузить")

        df.columns = df.columns.str.strip()

        logger.info(f"Загружено {len(df):,} строк")
        logger.info(f"Столбцы: {df.columns.tolist()}")

        return df

    except Exception as e:
        logger.error(f"Ошибка загрузки файла: {e}")
        raise


def validate_columns(df: pd.DataFrame) -> Tuple[bool, list]:
    df_columns = set([col.strip() for col in df.columns])
    required = set(REQUIRED_COLUMNS)

    missing = list(required - df_columns)

    if missing:
        logger.warning(f"Не найдено столбцов: {missing}")
        return False, missing

    logger.info("Все необходимые столбцы присутствуют")
    return True, []