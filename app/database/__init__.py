"""
Пакет database — слой работы с SQLite.

Предоставляет:
- Database — менеджер подключений
- ErrorLogRepository — репозиторий для логирования ошибок очистки данных
"""

from app.database.connection import Database
from app.database.repository import ErrorLogRepository

__all__ = [
    'Database',
    'ErrorLogRepository',
]