"""Инициализация рабочих директорий и БД при запуске."""

from app.config import (
    MODELS_DIR,
    DEBUG_DIR,
    RESULTS_DIR,
    FEATURES_DIR,
    RAW_DATA_DIR,
    DATA_DIR,
    DB_PATH,
)
from app.database import Database


def init_directories():
    """
    Создает необходимые директории проекта при запуске.
    Безопасно вызывается несколько раз (exist_ok=True).
    """

    for directory in [
        DATA_DIR,
        RAW_DATA_DIR,
        MODELS_DIR,
        DEBUG_DIR,
        RESULTS_DIR,
        FEATURES_DIR,
    ]:
        directory.mkdir(parents=True, exist_ok=True)


def init_database() -> Database:
    """Инициализирует SQLite БД и создаёт схему."""
    db = Database(str(DB_PATH))
    db.init_schema()
    return db
