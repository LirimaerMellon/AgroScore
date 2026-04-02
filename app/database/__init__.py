"""
Пакет database — слой работы с SQLite.

Предоставляет:
- Database — менеджер подключений
- ErrorLogRepository — лог ошибок очистки данных
- ModelRepository — реестр ML-моделей
- ApplicationRepository — оценённые заявки
"""

from app.database.connection import Database
from app.database.repository import ErrorLogRepository
from app.database.model_repository import ModelRepository
from app.database.app_repository import ApplicationRepository

__all__ = [
    'Database',
    'ErrorLogRepository',
    'ModelRepository',
    'ApplicationRepository',
]