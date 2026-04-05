"""
Пакет pipeline — компоненты ML-пайплайна.

Содержит загрузку данных, маппинг колонок, валидацию,
очистку, конструирование признаков, модель и SHAP-объяснения.
"""

from app.pipeline.loader import DataLoader
from app.pipeline.cleaner import DataCleaner
from app.pipeline.features import FeatureEngineer
from app.pipeline.model import ScoringModel
from app.pipeline.explainer import FeatureExplainer
from app.pipeline.validators import DataValidators
from app.pipeline.mapper import ColumnMapper

__all__ = [
    'DataLoader',
    'DataCleaner',
    'FeatureEngineer',
    'ScoringModel',
    'FeatureExplainer',
    'DataValidators',
    'ColumnMapper',
]