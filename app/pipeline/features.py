"""
FeatureEngineer — конструирование признаков для скоринга.

Ровно 10 признаков:
  Сырые (5):  amount, normative, district, subsidy_type, direction
  Производные (5):
    amount_to_normative        — amount / normative
    approval_rate_district     — ист. % одобрений по району
    approval_rate_subsidy_type — ист. % одобрений по виду субсидии
    amount_rank_in_subsidy_type — ранг суммы внутри вида субсидии (0–1)
    log_amount                 — ln(amount)

Архитектура fit / transform:
  - fit(df)           — вычисляет статистики из обучающих данных
  - transform(df)     — применяет сохранённые статистики к новым данным
  - fit_transform(df) — обучение + трансформация одним вызовом

Состояние (approval_rates, medians, known_categories)
сохраняется вместе с моделью для использования при inference.

ВАЖНО: region и akimat НЕ используются как фичи.
        district уже содержит географическую информацию.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Set

logger = logging.getLogger(__name__)


class FeatureEngineer:

    # Только 3 категориальных поля — они же фичи модели
    CATEGORICAL_FEATURES = ['district', 'subsidy_type', 'direction']
    SMOOTHING_WEIGHT = 10

    def __init__(self):
        self.approval_rates: Dict[str, pd.Series] = {}
        self._global_approval_rate: float = 0.0
        self._fill_medians: Dict[str, float] = {}
        self._known_categories: Dict[str, Set[str]] = {}
        self._fitted = False

    # ==========================================================
    # PUBLIC API
    # ==========================================================

    def fit(self, df: pd.DataFrame) -> 'FeatureEngineer':
        """Вычислить и сохранить статистики из обучающих данных."""
        logger.info("FeatureEngineer: fit...")
        self._calculate_approval_rates(df)
        self._save_known_categories(df)
        self._fitted = True
        logger.info("FeatureEngineer: fit завершён")
        return self

    def transform(self, df: pd.DataFrame, is_training: bool = True) -> pd.DataFrame:
        """Применить сохранённые статистики к данным."""
        if not self._fitted:
            raise RuntimeError("FeatureEngineer не обучен. Вызовите fit() сначала.")

        logger.info(f"FeatureEngineer: transform (training={is_training})...")
        df = df.copy()

        # 1. Approval rates (из saved state)
        df = self._add_approval_rate_features(df)

        # 2. Соотношение amount / normative
        df = self._add_ratio_features(df)

        # 3. Логарифм
        df = self._add_log_features(df)

        # 4. Ранг суммы внутри вида субсидии
        df = self._add_rank_features(df)

        # 5. Доля неизвестных категориальных полей (для confidence/review)
        if not is_training:
            df = self._add_unknown_ratio_feature(df)

        # 6. Заполнение пропусков
        df = self._fill_missing(df, is_training)

        logger.info(f"FeatureEngineer: transform завершён. Колонок: {len(df.columns)}")
        return df

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Обучить и применить за один вызов."""
        self.fit(df)
        return self.transform(df, is_training=True)

    # ==========================================================
    # FIT — вычисление статистик
    # ==========================================================

    def _calculate_approval_rates(self, df: pd.DataFrame) -> None:
        if 'is_approved' not in df.columns:
            logger.warning("'is_approved' отсутствует — approval rates не рассчитаны")
            return

        self._global_approval_rate = float(df['is_approved'].mean())
        m = self.SMOOTHING_WEIGHT

        for col in ['district', 'subsidy_type']:
            if col not in df.columns:
                continue
            grouped = df.groupby(col)['is_approved']
            count = grouped.count()
            mean = grouped.mean()
            smoothed = (count * mean + m * self._global_approval_rate) / (count + m)
            self.approval_rates[f'by_{col}'] = smoothed.astype(float)

        logger.info(
            f"Approval rates рассчитаны: "
            f"global={self._global_approval_rate:.3f}, "
            f"by_district={len(self.approval_rates.get('by_district', []))} значений, "
            f"by_subsidy_type={len(self.approval_rates.get('by_subsidy_type', []))} значений"
        )

    def _save_known_categories(self, df: pd.DataFrame) -> None:
        """Сохранить все известные значения категориальных признаков из обучающих данных."""
        for col in self.CATEGORICAL_FEATURES:
            if col in df.columns:
                unique_vals = set(df[col].dropna().astype(str).str.strip().unique())
                self._known_categories[col] = unique_vals
                logger.info(f"  {col}: {len(unique_vals)} уникальных значений")

    # ==========================================================
    # TRANSFORM — применение признаков
    # ==========================================================

    def _add_approval_rate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Добавляет approval_rate_district и approval_rate_subsidy_type.

        Для неизвестных значений при inference — глобальный средний approval_rate.
        """
        for col in ['district', 'subsidy_type']:
            key = f'by_{col}'
            if col in df.columns and key in self.approval_rates:
                df[f'approval_rate_{col}'] = df[col].map(self.approval_rates[key])
                df[f'approval_rate_{col}'] = df[f'approval_rate_{col}'].fillna(
                    self._global_approval_rate
                )
        return df

    def _add_ratio_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """amount_to_normative = amount / normative. NaN если normative == 0 или None."""
        if 'amount' in df.columns and 'normative' in df.columns:
            safe_normative = df['normative'].replace(0, np.nan)
            df['amount_to_normative'] = df['amount'] / safe_normative
        return df

    def _add_log_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """log_amount = ln(amount). NaN если amount <= 0."""
        if 'amount' in df.columns:
            df['log_amount'] = df['amount'].apply(
                lambda x: np.log(x) if (pd.notna(x) and x > 0) else np.nan
            )
        return df

    def _add_rank_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """amount_rank_in_subsidy_type — ранг суммы внутри вида субсидии (0–1)."""
        if 'amount' not in df.columns or 'subsidy_type' not in df.columns:
            return df
        df['amount_rank_in_subsidy_type'] = (
            df.groupby('subsidy_type')['amount'].rank(pct=True, method='average')
        )
        df['amount_rank_in_subsidy_type'] = df['amount_rank_in_subsidy_type'].fillna(0.5)
        return df

    def _add_unknown_ratio_feature(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Для inference: считаем долю категориальных признаков,
        значения которых НЕ были в обучающих данных.
        Высокий unknown_ratio → модель не может адекватно оценить заявку.
        """
        known_cats = getattr(self, '_known_categories', {})
        if not known_cats:
            df['unknown_ratio'] = 0.0
            return df

        checked = 0
        unknown_count = pd.Series(0, index=df.index, dtype=float)

        for col in self.CATEGORICAL_FEATURES:
            if col in df.columns and col in known_cats:
                checked += 1
                known_set = known_cats[col]
                is_unknown = ~df[col].astype(str).str.strip().isin(known_set)
                unknown_count += is_unknown.astype(float)

        if checked > 0:
            df['unknown_ratio'] = unknown_count / checked
        else:
            df['unknown_ratio'] = 0.0

        return df

    def _fill_missing(self, df: pd.DataFrame, is_training: bool) -> pd.DataFrame:
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        if is_training:
            for col in numeric_cols:
                if df[col].isna().any():
                    median_val = df[col].median()
                    self._fill_medians[col] = (
                        float(median_val) if not pd.isna(median_val) else 0.0
                    )
                    df[col] = df[col].fillna(self._fill_medians[col])
        else:
            for col in numeric_cols:
                if col == 'unknown_ratio':
                    continue
                if df[col].isna().any():
                    fill_val = self._fill_medians.get(col, 0.0)
                    df[col] = df[col].fillna(fill_val)

        return df

    # ==========================================================
    # QUERY — проверка данных
    # ==========================================================

    def get_unknown_fields(self, df: pd.DataFrame) -> list:
        """
        Для каждой строки возвращает список неизвестных полей.
        Используется ScoringService для предупреждений.
        Векторизованная реализация — isin() по колонкам вместо iterrows().
        """
        known_cats = getattr(self, '_known_categories', {})
        if not known_cats:
            return [[] for _ in range(len(df))]

        # Предвычисляем булевы маски для каждой категориальной колонки
        unknown_masks = {}
        for col in self.CATEGORICAL_FEATURES:
            if col in df.columns and col in known_cats:
                known_set = known_cats[col]
                unknown_masks[col] = ~df[col].astype(str).str.strip().isin(known_set)

        # Собираем результат из масок
        result = []
        for i in range(len(df)):
            unknowns = [col for col, mask in unknown_masks.items() if mask.iloc[i]]
            result.append(unknowns)
        return result

