"""
Пакет database — слой работы с SQLite.

Предоставляет:
- Database — менеджер подключений
- ErrorLogRepository — лог ошибок очистки данных
- ModelRepository — реестр ML-моделей
- ApplicationRepository — оценённые заявки
- ShapRepository — SHAP-объяснения
- ThresholdRepository — пороги категорий и бюджет раунда
"""

from app.database.connection import Database
from app.database.repository import ErrorLogRepository
from app.database.model_repository import ModelRepository
from app.database.app_repository import ApplicationRepository
from app.database.shap_repository import ShapRepository
from app.database.threshold_repository import ThresholdRepository

__all__ = [
    'Database',
    'ErrorLogRepository',
    'ModelRepository',
    'ApplicationRepository',
    'ShapRepository',
    'ThresholdRepository',
]