"""
DataCleaner — очистка и подготовка данных под ML.

Поддерживает два режима:
  mode='training'  — полная валидация (даты, статусы, номер заявки)
  mode='inference'  — только числовые и категориальные проверки

Каждая исключённая запись сохраняется в error_logs (SQLite)
с полным контекстом для отображения на фронтенде.
"""

import pandas as pd
import logging
import re
from typing import Optional, List, Dict, Any

from app.pipeline.validators import DataValidators
from app.database.repository import ErrorLogRepository
from app.config import (
    DATE_COLUMN,
    NUMERIC_COLUMNS,
    CATEGORICAL_COLUMNS,
    INFERENCE_CATEGORICAL_COLUMNS,
    APPROVED_STATUSES,
    REJECTED_STATUSES,
    COLUMN_DISPLAY_MAP,
)

logger = logging.getLogger(__name__)


class DataCleaner:
    """
    Очистка входного датасета с логированием ошибок в SQLite.

    Использование:
        cleaner = DataCleaner(error_repo=repo)
        cleaned = cleaner.clean_data(df, source_name='file.xlsx', mode='training')
        cleaned = cleaner.add_target_variable(cleaned)
    """

    def __init__(
        self,
        error_repo: Optional[ErrorLogRepository] = None,
        logger_instance: Optional[logging.Logger] = None,
    ):
        self.error_repo = error_repo
        self.logger = logger_instance or logging.getLogger(__name__)
        self.last_trace_id: Optional[str] = None

    # ==================================================================
    # PUBLIC
    # ==================================================================

    def clean_data(
        self,
        df: pd.DataFrame,
        source_name: str = "unknown",
        source_type: str = "excel",
        mode: str = "training",
    ) -> pd.DataFrame:
        """
        Очистка входного датасета.

        mode='training':
            1. Пустые строки  2. Номер заявки  3. Дубликаты
            4. Даты  5. Числа  6. Категории (с status)
        mode='inference':
            1. Пустые строки  5. Числа  6. Категории (без status)
        """
        df = df.copy()
        initial_rows = len(df)

        self.last_trace_id = (
            ErrorLogRepository.create_trace() if self.error_repo else None
        )
        trace = self.last_trace_id

        # 1. Полностью пустые строки
        empty_mask = df.isna().all(axis=1)
        if empty_mask.any():
            self._log_batch(
                df[empty_mask], trace, source_type, source_name,
                error_code="empty_row", error_cols=[], msg="Полностью пустая строка",
            )
            df = df[~empty_mask]

        if mode == "training":
            # 2. Нет номера заявки
            if "request_number" in df.columns:
                no_rn = df["request_number"].isna()
                if no_rn.any():
                    self._log_batch(
                        df[no_rn], trace, source_type, source_name,
                        error_code="required_field", error_cols=["request_number"],
                        msg="Отсутствует номер заявки",
                    )
                    df = df[~no_rn]

            # 3. Дубликаты
            dup_mask = df.duplicated(keep="first")
            if dup_mask.any():
                self._log_batch(
                    df[dup_mask], trace, source_type, source_name,
                    error_code="duplicate", error_cols=[], msg="Дублирующая запись",
                )
                df = df[~dup_mask]

            # 4. Дата
            if DATE_COLUMN in df.columns:
                df[DATE_COLUMN] = pd.to_datetime(df[DATE_COLUMN], errors="coerce")
                bad_date = df[DATE_COLUMN].isna()
                if bad_date.any():
                    self._log_batch(
                        df[bad_date], trace, source_type, source_name,
                        error_code="invalid_date", error_cols=[DATE_COLUMN],
                        msg="Некорректный формат даты",
                    )
                    df = df[~bad_date]

        # 5. Числовые колонки — нормализация и валидация
        for col in NUMERIC_COLUMNS:
            if col not in df.columns:
                continue

            # Нормализация: "100.000" → 100000, "1.000.000,50" → 1000000.5
            df[col] = df[col].apply(self._normalize_numeric)

            not_num = ~df[col].apply(DataValidators.is_strict_number)
            if not_num.any():
                self._log_batch(
                    df[not_num], trace, source_type, source_name,
                    error_code="invalid_format", error_cols=[col],
                    msg=f"Значение в «{self._display(col)}» не является числом",
                )
                df = df[~not_num]

            df[col] = df[col].astype(float)

            non_pos = df[col] <= 0
            if non_pos.any():
                self._log_batch(
                    df[non_pos], trace, source_type, source_name,
                    error_code="non_positive_value", error_cols=[col],
                    msg=f"Значение в «{self._display(col)}» должно быть > 0",
                )
                df = df[~non_pos]

        # 6. Категориальные колонки
        cat_cols = CATEGORICAL_COLUMNS if mode == "training" else INFERENCE_CATEGORICAL_COLUMNS
        for col in cat_cols:
            if col not in df.columns:
                continue

            bad_text = ~df[col].apply(DataValidators.is_valid_text)
            if bad_text.any():
                self._log_batch(
                    df[bad_text], trace, source_type, source_name,
                    error_code="invalid_text", error_cols=[col],
                    msg=f"Пустое или невалидное значение в «{self._display(col)}»",
                )
                df = df[~bad_text]

            df[col] = (
                df[col].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
            )

        removed = initial_rows - len(df)
        self.logger.info(
            f"Очистка [{mode}] завершена: осталось {len(df)} строк, удалено {removed}"
        )
        return df

    def add_target_variable(
        self,
        df: pd.DataFrame,
        source_name: str = "unknown",
        source_type: str = "excel",
    ) -> pd.DataFrame:
        """
        Формирование целевой переменной (target).
        Используется только для обучения.
        """
        df = df.copy()
        trace = self.last_trace_id

        if "status" not in df.columns:
            raise ValueError("Отсутствует столбец: статус заявки")

        df["status"] = df["status"].astype(str).str.lower().str.strip()

        df["is_approved"] = -1
        df.loc[df["status"].isin(APPROVED_STATUSES), "is_approved"] = 1
        df.loc[df["status"].isin(REJECTED_STATUSES), "is_approved"] = 0

        before = len(df)

        intermediate = df["is_approved"] == -1
        if intermediate.any():
            self.logger.info(
                f"Промежуточные статусы ({intermediate.sum()} строк) исключены из обучения "
                f"(не являются ошибками)"
            )

        df = df[df["is_approved"] != -1]

        approved = int((df["is_approved"] == 1).sum())
        rejected = int((df["is_approved"] == 0).sum())
        removed = before - len(df)

        self.logger.info(f"Одобрено: {approved}  |  Отклонено: {rejected}  |  Удалено (промежуточные): {removed}")
        return df

    # ==================================================================
    # PRIVATE
    # ==================================================================

    def _log_batch(
        self,
        df_bad: pd.DataFrame,
        trace_id: Optional[str],
        source_type: str,
        source_name: str,
        error_code: str,
        error_cols: List[str],
        msg: str,
    ) -> None:
        count = len(df_bad)
        self.logger.debug(f"  [{error_code}] {msg} — {count} строк")

        if self.error_repo is None or trace_id is None:
            return

        display_cols = [self._display(c) for c in error_cols]

        entries: List[Dict[str, Any]] = []
        records = df_bad.to_dict("index")

        for idx, row_data in records.items():
            violations = [
                {
                    "code": error_code,
                    "cols": error_cols,
                    "msg": msg,
                    "display": ", ".join(display_cols) if display_cols else "—",
                }
            ]

            entries.append(
                {
                    "trace_id": trace_id,
                    "source_type": source_type,
                    "source_name": source_name,
                    "error_codes": [error_code],
                    "error_cols": error_cols,
                    "locator": {"row": int(idx) + 2},
                    "raw_payload": row_data,
                    "violations": violations,
                }
            )

        self.error_repo.log_errors_batch(entries)

    @staticmethod
    def _display(col: str) -> str:
        return COLUMN_DISPLAY_MAP.get(col, col)

    @staticmethod
    def _normalize_numeric(value):
        """
        Нормализация числовых значений с учётом формата CIS/Европа:
          - точка как разделитель тысяч: 100.000 → 100000
          - запятая как десятичный: 100.000,50 → 100000.5
          - пробел как разделитель тысяч: 100 000 → 100000
        Если значение уже числовое (int/float) — возвращается как есть.
        """
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value
        if pd.isna(value):
            return value

        s = str(value).strip().replace('\xa0', '').replace(' ', '')
        if not s:
            return value

        # Формат: "1.000.000,50" или "100.000,50" (точка=тысячи, запятая=десятичная)
        if re.match(r'^\d{1,3}(\.\d{3})+(,\d+)?$', s):
            s = s.replace('.', '').replace(',', '.')
            try:
                return float(s)
            except ValueError:
                return value

        # Формат: "100.000" (точка=тысячи, без десятичной)
        # Определяем: если после каждой точки ровно 3 цифры — это тысячный разделитель
        if re.match(r'^\d{1,3}(\.\d{3})+$', s):
            s = s.replace('.', '')
            try:
                return float(s)
            except ValueError:
                return value

        # Формат: "1000,50" (запятая=десятичная, без точек-тысяч)
        if re.match(r'^\d+(,\d+)$', s):
            s = s.replace(',', '.')
            try:
                return float(s)
            except ValueError:
                return value

        # Обычное число: "100.5", "100" — стандартная попытка
        try:
            return float(s)
        except ValueError:
            return value

