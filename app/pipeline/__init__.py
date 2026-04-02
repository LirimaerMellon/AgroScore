"""
__init__.py для пакета pipeline

Назначение:
- Формирует единый публичный API пайплайна
- Скрывает внутреннюю структуру модулей
- Позволяет удобно импортировать компоненты системы
"""

from app.pipeline.loader import DataLoader
from app.pipeline.cleaner import DataCleaner
from app.pipeline.features import FeatureEngineer
from app.pipeline.model import ScoringModel
from app.pipeline.explainer import FeatureExplainer
from app.pipeline.validators import DataValidators
from app.pipeline.mapper import ColumnMapper

# =========================
# ПУБЛИЧНЫЙ API ПАКЕТА
# =========================

__all__ = [
    # loader
    'DataLoader',

    # cleaner
    'DataCleaner',

    # features
    'FeatureEngineer',

    # model
    'ScoringModel',

    # explainer
    'FeatureExplainer',

    # validators
    'DataValidators',

    # mapper
    'ColumnMapper'
]