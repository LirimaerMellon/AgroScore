import pandas as pd
import numpy as np
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class FeatureEngineer:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.approval_rates = {}
        self.aggregates = {}

    def calculate_approval_rates(self) -> Dict:
        logger.info("Расчет показателей одобрения...")

        if 'is_approved' not in self.df.columns:
            logger.warning("Отсутствует переменная is_approved")
            return {}

        df_with_status = self.df[self.df['is_approved'] != -1].copy()

        if len(df_with_status) == 0:
            logger.warning("Нет нужного статуса в данных")
            return {}

        rates = {}

        if 'region' in df_with_status.columns:
            rates['by_region'] = df_with_status.groupby('region')['is_approved'].mean()

        if 'subsidy_type' in df_with_status.columns:
            rates['by_subsidy_type'] = df_with_status.groupby('subsidy_type')['is_approved'].mean()

        if 'direction' in df_with_status.columns:
            rates['by_direction'] = df_with_status.groupby('direction')['is_approved'].mean()

        self.approval_rates = rates

        logger.info(f"Рассчитаны показатели одобрения")

        return rates

    def calculate_financial_aggregates(self) -> Dict:
        logger.info("Расчет финансовых агрегатов...")

        aggregates = {}

        if 'region' in self.df.columns:
            agg = self.df.groupby('region').agg({
                'amount': ['sum', 'mean', 'count'],
                'normative': 'mean'
            }).round(2)

            agg.columns = ['total_amount_region', 'avg_amount_region', 'count_region', 'avg_norm_region']
            aggregates['by_region'] = agg

        if 'subsidy_type' in self.df.columns:
            agg = self.df.groupby('subsidy_type').agg({
                'amount': ['sum', 'mean', 'count']
            }).round(2)

            agg.columns = ['total_amount_subsidy', 'avg_amount_subsidy', 'count_subsidy']
            aggregates['by_subsidy_type'] = agg

        if 'direction' in self.df.columns:
            agg = self.df.groupby('direction').agg({
                'amount': ['sum', 'mean', 'count']
            }).round(2)

            agg.columns = ['total_amount_direction', 'avg_amount_direction', 'count_direction']
            aggregates['by_direction'] = agg

        self.aggregates = aggregates

        logger.info("Рассчитанны финансовые агрегаты")

        return aggregates

    def enrich_dataset(self) -> pd.DataFrame:
        logger.info("Загрузка набора данных...")

        df = self.df.copy()
        features_added = 0

        # Approval rates
        if 'region' in df.columns and 'by_region' in self.approval_rates:
            df['approval_rate_region'] = df['region'].map(
                self.approval_rates['by_region']
            )

        if 'subsidy_type' in df.columns and 'by_subsidy_type' in self.approval_rates:
            df['approval_rate_subsidy'] = df['subsidy_type'].map(
                self.approval_rates['by_subsidy_type']
            )

        if 'direction' in df.columns and 'by_direction' in self.approval_rates:
            df['approval_rate_direction'] = df['direction'].map(
                self.approval_rates['by_direction']
            )

        # Financial aggregates
        if 'region' in df.columns and 'by_region' in self.aggregates:
            for col in self.aggregates['by_region'].columns:
                df[col] = df['region'].map(self.aggregates['by_region'][col])

        if 'subsidy_type' in df.columns and 'by_subsidy_type' in self.aggregates:
            for col in self.aggregates['by_subsidy_type'].columns:
                df[col] = df['subsidy_type'].map(self.aggregates['by_subsidy_type'][col])

        if 'direction' in df.columns and 'by_direction' in self.aggregates:
            for col in self.aggregates['by_direction'].columns:
                df[col] = df['direction'].map(self.aggregates['by_direction'][col])

        # Time features
        if 'date' in df.columns:
            df['days_since_application'] = (
                pd.Timestamp.now() - df['date']
            ).dt.days.clip(lower=0)

        # Log transform
        if 'amount' in df.columns:
            df['log_amount'] = np.log1p(df['amount'])

        # Fill NaN for numeric features
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].mean())

        logger.info(f"Набор данных загружен. Столбцов: {len(df.columns)}")

        return df