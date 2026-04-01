import pandas as pd
import numpy as np
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    Класс для feature engineering в pipeline скоринга сельхозпроизводителей.

    Отвечает за:
    - Расчет агрегированных статистик (approval rates, aggregates)
    - Обогащение датасета признаками для merit-based скоринга
    - Подготовку данных для ML модели

    Порядок вызова:
        fe = FeatureEngineer(df)
        fe.calculate_approval_rates()
        fe.calculate_financial_aggregates()
        enriched_df = fe.enrich_dataset()
    """

    # Категориальные колонки для группировки
    GROUP_COLUMNS = ['region', 'subsidy_type', 'direction', 'district', 'akimat']

    # Вес глобального prior для байесовского сглаживания
    SMOOTHING_WEIGHT = 10

    def __init__(self, df: pd.DataFrame):
        """
        Инициализация класса.
        """
        self.df = df.copy()
        self.approval_rates: Dict[str, pd.Series] = {}
        self.aggregates: Dict[str, pd.DataFrame] = {}
        self._global_approval_rate: float = 0.0

    # =========================
    # APPROVAL RATES
    # =========================
    def calculate_approval_rates(self) -> Dict[str, pd.Series]:
        """
        Расчет доли одобрений (approval rate) по категориям
        с байесовским сглаживанием для малых групп.

        Формула: (n * mean + m * prior) / (n + m)
        где m — вес prior, prior — глобальный approval rate.
        """

        logger.info("Начало расчета показателей одобрения...")

        if 'is_approved' not in self.df.columns:
            logger.error("Колонка 'is_approved' отсутствует в данных")
            return {}

        # Глобальный средний approval rate (prior для сглаживания)
        self._global_approval_rate = float(self.df['is_approved'].mean())

        rates: Dict[str, pd.Series] = {}
        m = self.SMOOTHING_WEIGHT

        for col in self.GROUP_COLUMNS:
            if col not in self.df.columns:
                logger.warning(f"Колонка '{col}' отсутствует, пропускаем расчет")
                continue

            grouped = self.df.groupby(col)['is_approved']
            count = grouped.count()
            mean = grouped.mean()

            # Байесовское сглаживание — защита от ненадежных оценок
            smoothed = (count * mean + m * self._global_approval_rate) / (count + m)

            rates[f'by_{col}'] = smoothed.astype(float)

        self.approval_rates = rates

        logger.info("Расчет approval rates завершен.")

        return rates

    # =========================
    # FINANCIAL AGGREGATES
    # =========================
    def calculate_financial_aggregates(self) -> Dict[str, pd.DataFrame]:
        """
        Расчет финансовых агрегатов по категориям.

        Для каждой группы считаем:
        - sum, mean, median, std, count по amount
        - mean по normative
        """

        logger.info("Начало расчета финансовых агрегатов...")

        aggregates: Dict[str, pd.DataFrame] = {}

        has_amount = 'amount' in self.df.columns
        has_normative = 'normative' in self.df.columns

        if not has_amount:
            logger.warning("Колонка 'amount' отсутствует, агрегаты не рассчитаны.")
            return {}

        for col in self.GROUP_COLUMNS:
            if col not in self.df.columns:
                logger.warning(f"Колонка '{col}' отсутствует, агрегаты не рассчитаны.")
                continue

            prefix = col

            agg_dict = {
                'amount': ['sum', 'mean', 'median', 'std', 'count']
            }
            if has_normative:
                agg_dict['normative'] = ['mean']

            agg = self.df.groupby(col).agg(agg_dict).round(2)

            # Переименование MultiIndex колонок в плоский формат
            new_cols = []
            for top, sub in agg.columns:
                if sub == 'count':
                    new_cols.append(f'count_{prefix}')
                else:
                    new_cols.append(f'{sub}_{top}_{prefix}')
            agg.columns = new_cols

            # Заполняем NaN std для групп из одного элемента
            std_col = f'std_amount_{prefix}'
            if std_col in agg.columns:
                agg[std_col] = agg[std_col].fillna(0)

            aggregates[f'by_{col}'] = agg

        self.aggregates = aggregates

        logger.info("Финансовые агрегаты успешно рассчитаны.")

        return aggregates

    # =========================
    # FEATURE ENRICHMENT
    # =========================
    def enrich_dataset(self) -> pd.DataFrame:
        """
        Обогащение датасета признаками для merit-based скоринга.

        ВАЖНО: вызывать после calculate_approval_rates и calculate_financial_aggregates
        """

        logger.info("Начало обогащения датасета признаками...")

        df = self.df.copy()

        # 1. Approval rate по категориям
        df = self._add_approval_rate_features(df)

        # 2. Финансовые агрегаты
        df = self._add_aggregate_features(df)

        # 3. Соотношения числовых признаков
        df = self._add_ratio_features(df)

        # 4. Логарифмические трансформации
        df = self._add_log_features(df)

        # 5. Временные признаки
        df = self._add_time_features(df)

        # 6. Ранговые признаки (процентиль суммы внутри группы)
        df = self._add_rank_features(df)

        # 7. Z-score отклонения от средней по группе
        df = self._add_deviation_features(df)

        # 8. Комбинированные категориальные признаки
        df = self._add_interaction_features(df)

        # 9. Заполнение пропусков
        df = self._fill_missing(df)

        logger.info(f"Обогащение завершено. Количество колонок: {len(df.columns)}")

        return df

    # =========================
    # PRIVATE HELPERS
    # =========================

    def _add_approval_rate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Маппинг предрассчитанных approval rates на датасет."""

        if not self.approval_rates:
            return df

        for col in self.GROUP_COLUMNS:
            key = f'by_{col}'
            if col in df.columns and key in self.approval_rates:
                df[f'approval_rate_{col}'] = df[col].map(self.approval_rates[key])

        return df

    def _add_aggregate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Присоединение предрассчитанных финансовых агрегатов."""

        if not self.aggregates:
            return df

        for group_key, agg_df in self.aggregates.items():
            group_col = group_key.replace('by_', '')

            if group_col not in df.columns:
                logger.warning(f"Колонка '{group_col}' отсутствует для агрегатов.")
                continue

            for feat_col in agg_df.columns:
                df[feat_col] = df[group_col].map(agg_df[feat_col])

        return df

    def _add_ratio_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Соотношения между числовыми признаками."""

        if 'amount' in df.columns and 'normative' in df.columns:
            # Защита от деления на ноль
            safe_normative = df['normative'].replace(0, np.nan)
            df['amount_to_normative'] = (df['amount'] / safe_normative).fillna(0)

        return df

    def _add_log_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Логарифмические трансформации для сглаживания распределений."""

        if 'amount' in df.columns:
            df['log_amount'] = np.log1p(df['amount'])

        if 'normative' in df.columns:
            df['log_normative'] = np.log1p(df['normative'])

        return df

    def _add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Признаки на основе даты подачи заявки."""

        if 'submission_date' not in df.columns:
            return df

        try:
            df['submission_date'] = pd.to_datetime(df['submission_date'], errors='coerce')

            # Используем максимальную дату в данных как reference —
            # стабильный признак, не зависящий от момента запуска
            reference_date = df['submission_date'].max()

            if pd.isna(reference_date):
                logger.warning("Все даты невалидны, временные признаки не созданы.")
                return df

            # Количество дней с момента подачи до reference_date
            df['days_since_submission'] = (
                (reference_date - df['submission_date']).dt.days
            ).clip(lower=0)

            # Временные признаки
            df['month'] = df['submission_date'].dt.month
            df['quarter'] = df['submission_date'].dt.quarter
            df['day_of_week'] = df['submission_date'].dt.dayofweek
            df['day'] = df['submission_date'].dt.day

        except Exception as e:
            logger.error(f"Ошибка при обработке даты: {e}")

        return df

    def _add_rank_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ранговые признаки — процентиль суммы внутри группы."""

        if 'amount' not in df.columns:
            return df

        for col in ['region', 'subsidy_type', 'direction']:
            if col not in df.columns:
                continue

            df[f'amount_rank_in_{col}'] = (
                df.groupby(col)['amount']
                .rank(pct=True, method='average')
            )

        return df

    def _add_deviation_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Отклонение суммы от средней по группе (z-score)."""

        if 'amount' not in df.columns:
            return df

        for col in ['region', 'subsidy_type']:
            if col not in df.columns:
                continue

            group_mean = df.groupby(col)['amount'].transform('mean')
            group_std = df.groupby(col)['amount'].transform('std').replace(0, np.nan)

            df[f'amount_zscore_{col}'] = (
                (df['amount'] - group_mean) / group_std
            ).fillna(0)

        return df

    def _add_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Комбинированные категориальные признаки для перекрёстных паттернов."""

        pairs = [
            ('region', 'direction'),
            ('region', 'subsidy_type'),
        ]

        for col_a, col_b in pairs:
            if col_a in df.columns and col_b in df.columns:
                df[f'{col_a}_x_{col_b}'] = (
                    df[col_a].astype(str) + '_' + df[col_b].astype(str)
                )

        return df

    def _fill_missing(self, df: pd.DataFrame) -> pd.DataFrame:
        """Заполнение пропусков медианой для числовых признаков."""

        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            if df[col].isna().any():
                df[col] = df[col].fillna(df[col].median())

        return df