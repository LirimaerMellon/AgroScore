import pandas as pd


class DataValidators:
    """
    Набор утилит для валидации данных.
    Используется в preprocessing / cleaning слоях.
    """

    @staticmethod
    def is_strict_number(value) -> bool:
        """
        Проверяет, что значение:
        - не NaN
        - является int или float
        - не является bool
        """
        if pd.isna(value):
            return False
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    @staticmethod
    def is_valid_text(value) -> bool:
        """
        Проверяет, что значение:
        - не NaN
        - является строкой
        - не пустая строка после strip()
        """
        if pd.isna(value):
            return False

        if not isinstance(value, str):
            return False

        return value.strip() != ""