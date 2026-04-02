"""
ColumnMapper — маппинг колонок из разных форматов в единую internal-схему.

Поддерживает два режима:
- training: Excel с историческими данными (русские заголовки → internal)
- inference: Excel-шаблон с данными для скоринга (русские или English → internal)

Также поддерживает входные данные уже в English-формате (JSON).
"""

import pandas as pd
import logging
from typing import List

from app.config import (
    COLUMN_RENAME_MAP,
    INFERENCE_RENAME_MAP,
    REQUIRED_COLUMNS,
    INFERENCE_REQUIRED_COLUMNS,
)

logger = logging.getLogger(__name__)


class ColumnMapper:

    def map_training(self, df: pd.DataFrame) -> pd.DataFrame:
        """Маппинг Excel-файла обучения → internal names."""
        df = df.copy()
        df.columns = df.columns.str.strip()
        df = df.rename(columns=COLUMN_RENAME_MAP)
        return df

    def map_inference(self, df: pd.DataFrame) -> pd.DataFrame:
        """Маппинг Excel-шаблона inference → internal names."""
        df = df.copy()
        df.columns = df.columns.str.strip()
        df = df.rename(columns=INFERENCE_RENAME_MAP)
        return df

    @staticmethod
    def validate_training(df: pd.DataFrame) -> None:
        """Проверка обязательных колонок для обучения."""
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(
                f"Отсутствуют обязательные колонки для обучения: {missing}"
            )

    @staticmethod
    def validate_inference(df: pd.DataFrame) -> None:
        """Проверка обязательных колонок для inference."""
        missing = [c for c in INFERENCE_REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(
                f"Отсутствуют обязательные колонки для скоринга: {missing}"
            )

