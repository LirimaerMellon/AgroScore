"""
FeatureEngineer — конструирование признаков для скоринга.

Архитектура fit / transform:
  - fit(df)           — вычисляет статистики из обучающих данных
  - transform(df)     — применяет сохранённые статистики к новым данным
  - fit_transform(df) — обучение + трансформация одним вызовом

Состояние (approval_rates, aggregates, group_stats, medians)
сохраняется вместе с моделью для использования при inference.

ВАЖНО: Временные признаки (дата, месяц, день) НЕ используются.
Скоринг основан только на атрибутах заявки и исторических паттернах.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Optional, Set

logger = logging.getLogger(__name__)


class FeatureEngineer:

    GROUP_COLUMNS = ['region', 'subsidy_type', 'direction', 'district', 'akimat']
    SMOOTHING_WEIGHT = 10

    def __init__(self):
        self.approval_rates: Dict[str, pd.Series] = {}
        self.aggregates: Dict[str, pd.DataFrame] = {}
        self._global_approval_rate: float = 0.0
        self._fill_medians: Dict[str, float] = {}
        self._fill_q25: Dict[str, float] = {}          # 25-й перцентиль для пессимистичного заполнения
        self._group_amount_stats: Dict[str, Dict] = {}
        self._known_categories: Dict[str, Set[str]] = {}
        self._fitted = False

    # ==========================================================
    # PUBLIC API
    # ==========================================================

    def fit(self, df: pd.DataFrame) -> 'FeatureEngineer':
        """Вычислить и сохранить статистики из обучающих данных."""
        logger.info("FeatureEngineer: fit...")
        self._calculate_approval_rates(df)
        self._calculate_financial_aggregates(df)
        self._calculate_group_stats(df)
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

        # 2. Финансовые агрегаты (из saved state)
        df = self._add_aggregate_features(df)

        # 3. Соотношения
        df = self._add_ratio_features(df)

        # 4. Логарифмы
        df = self._add_log_features(df)

        # 5. Ранги
        df = self._add_rank_features(df)

        # 6. Z-score отклонения
        df = self._add_deviation_features(df, is_training)

        # 7. Комбинированные категориальные
        df = self._add_interaction_features(df)

        # 8. Доля неизвестных категориальных значений (штраф за мусор)
        if not is_training:
            df = self._add_unknown_ratio_feature(df)

        # 9. Заполнение пропусков
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

        for col in self.GROUP_COLUMNS:
            if col not in df.columns:
                continue
            grouped = df.groupby(col)['is_approved']
            count = grouped.count()
            mean = grouped.mean()
            smoothed = (count * mean + m * self._global_approval_rate) / (count + m)
            self.approval_rates[f'by_{col}'] = smoothed.astype(float)

        logger.info("Approval rates рассчитаны")

    def _calculate_financial_aggregates(self, df: pd.DataFrame) -> None:
        if 'amount' not in df.columns:
            return

        has_normative = 'normative' in df.columns

        for col in self.GROUP_COLUMNS:
            if col not in df.columns:
                continue

            agg_dict = {'amount': ['sum', 'mean', 'median', 'std', 'count']}
            if has_normative:
                agg_dict['normative'] = ['mean']

            agg = df.groupby(col).agg(agg_dict).round(2)

            new_cols = []
            for top, sub in agg.columns:
                if sub == 'count':
                    new_cols.append(f'count_{col}')
                else:
                    new_cols.append(f'{sub}_{top}_{col}')
            agg.columns = new_cols

            std_col = f'std_amount_{col}'
            if std_col in agg.columns:
                agg[std_col] = agg[std_col].fillna(0)

            self.aggregates[f'by_{col}'] = agg

        logger.info("Финансовые агрегаты рассчитаны")

    def _calculate_group_stats(self, df: pd.DataFrame) -> None:
        """Средние и std по группам — для z-score при inference."""
        if 'amount' not in df.columns:
            return
        for col in self.GROUP_COLUMNS:
            if col not in df.columns:
                continue
            stats = df.groupby(col)['amount'].agg(['mean', 'std']).fillna(0)
            self._group_amount_stats[col] = stats.to_dict('index')

    def _save_known_categories(self, df: pd.DataFrame) -> None:
        """Сохранить все известные значения категориальных признаков из обучающих данных."""
        for col in self.GROUP_COLUMNS:
            if col in df.columns:
                unique_vals = set(df[col].dropna().astype(str).str.strip().unique())
                self._known_categories[col] = unique_vals
                logger.info(f"  {col}: {len(unique_vals)} уникальных значений")

    # ==========================================================
    # TRANSFORM — применение признаков
    # ==========================================================

    def _add_approval_rate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        # Для неизвестных категорий — нейтральный prior:
        # глобальный средний × 0.8 (20% «скидка за новизну»).
        # Это справедливо: новый фермер не наказывается, но и не получает
        # бонуса от лучших регионов. Лёгкий дисконт за отсутствие истории.
        novelty_prior = self._global_approval_rate * 0.8

        for col in self.GROUP_COLUMNS:
            key = f'by_{col}'
            if col in df.columns and key in self.approval_rates:
                df[f'approval_rate_{col}'] = df[col].map(self.approval_rates[key])
                df[f'approval_rate_{col}'] = df[f'approval_rate_{col}'].fillna(
                    novelty_prior
                )
        return df

    def _add_aggregate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        for group_key, agg_df in self.aggregates.items():
            group_col = group_key.replace('by_', '')
            if group_col not in df.columns:
                continue
            for feat_col in agg_df.columns:
                df[feat_col] = df[group_col].map(agg_df[feat_col])
        return df

    def _add_ratio_features(self, df: pd.DataFrame) -> pd.DataFrame:
        if 'amount' in df.columns and 'normative' in df.columns:
            safe_normative = df['normative'].replace(0, np.nan)
            df['amount_to_normative'] = (df['amount'] / safe_normative).fillna(0)
        return df

    def _add_log_features(self, df: pd.DataFrame) -> pd.DataFrame:
        if 'amount' in df.columns:
            df['log_amount'] = np.log1p(df['amount'])
        if 'normative' in df.columns:
            df['log_normative'] = np.log1p(df['normative'])
        return df

    def _add_rank_features(self, df: pd.DataFrame) -> pd.DataFrame:
        if 'amount' not in df.columns:
            return df
        for col in ['region', 'subsidy_type', 'direction']:
            if col not in df.columns:
                continue
            df[f'amount_rank_in_{col}'] = (
                df.groupby(col)['amount'].rank(pct=True, method='average')
            )
            df[f'amount_rank_in_{col}'] = df[f'amount_rank_in_{col}'].fillna(0.5)
        return df

    def _add_deviation_features(
        self, df: pd.DataFrame, is_training: bool
    ) -> pd.DataFrame:
        """Z-score отклонения суммы от средней по группе."""
        if 'amount' not in df.columns:
            return df

        for col in ['region', 'subsidy_type']:
            if col not in df.columns:
                continue

            if is_training:
                group_mean = df.groupby(col)['amount'].transform('mean')
                group_std = df.groupby(col)['amount'].transform('std').replace(0, np.nan)
                df[f'amount_zscore_{col}'] = (
                    (df['amount'] - group_mean) / group_std
                ).fillna(0)
            else:
                # Inference — используем сохранённые статистики
                if col in self._group_amount_stats:
                    stats = self._group_amount_stats[col]
                    means = df[col].map(
                        {k: v['mean'] for k, v in stats.items()}
                    )
                    stds = df[col].map(
                        {k: v['std'] for k, v in stats.items()}
                    ).replace(0, np.nan)
                    df[f'amount_zscore_{col}'] = (
                        (df['amount'] - means) / stds
                    ).fillna(0)
                else:
                    df[f'amount_zscore_{col}'] = 0

        return df

    def _add_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        pairs = [('region', 'direction'), ('region', 'subsidy_type')]
        for col_a, col_b in pairs:
            if col_a in df.columns and col_b in df.columns:
                df[f'{col_a}_x_{col_b}'] = (
                    df[col_a].astype(str) + '_' + df[col_b].astype(str)
                )
        return df

    def _add_unknown_ratio_feature(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Для inference: считаем долю категориальных признаков,
        значения которых НЕ были в обучающих данных.
        Высокий unknown_ratio → модель не может адекватно оценить заявку.
        """
        known_cats = getattr(self, '_known_categories', {})
        if not known_cats:
            return df

        checked = 0
        unknown_count = pd.Series(0, index=df.index, dtype=float)

        for col in self.GROUP_COLUMNS:
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
                    q25_val = df[col].quantile(0.25)
                    self._fill_q25[col] = (
                        float(q25_val) if not pd.isna(q25_val) else 0.0
                    )
                    df[col] = df[col].fillna(self._fill_medians[col])
        else:
            # Enterprise-подход: заполняем медианой (нейтральная оценка).
            # Неизвестная группа → «средний» уровень агрегатов, не плохой и не хороший.
            # Дисконт за неизвестность уже учтён в confidence penalty.
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
        """
        known_cats = getattr(self, '_known_categories', {})
        result = []
        for idx, row in df.iterrows():
            unknowns = []
            for col in self.GROUP_COLUMNS:
                if col in df.columns and col in known_cats:
                    val = str(row[col]).strip()
                    if val not in known_cats[col]:
                        unknowns.append(col)
            result.append(unknowns)
        return result

