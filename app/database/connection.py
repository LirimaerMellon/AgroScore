"""
Менеджер подключений к SQLite.

- Создаёт файл БД и родительские папки автоматически
- WAL-режим для параллельного чтения
- Context manager для безопасных транзакций

Таблицы:
- error_logs   — лог невалидных строк при очистке данных
- models       — реестр обученных ML-моделей
- applications — оценённые заявки (inference)
"""

import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class Database:

    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    # Connection
    @contextmanager
    def get_connection(self):
        """
        Возвращает соединение внутри контекстного менеджера.
        Автоматический commit / rollback.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # Schema
    def init_schema(self):
        """
        Создаёт таблицы и индексы.
        """
        with self.get_connection() as conn:
            # --- error_logs ---
            conn.execute("""
                CREATE TABLE IF NOT EXISTS error_logs (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    trace_id    TEXT    NOT NULL,
                    detected_at TEXT    NOT NULL,
                    source_type TEXT    NOT NULL,
                    source_name TEXT    NOT NULL,
                    error_codes TEXT    NOT NULL DEFAULT '[]',
                    error_cols  TEXT    NOT NULL DEFAULT '[]',
                    locator     TEXT    NOT NULL,
                    raw_payload TEXT,
                    violations  TEXT    NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_el_trace ON error_logs(trace_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_el_source ON error_logs(source_name)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_el_detected ON error_logs(detected_at)"
            )

            # --- models ---
            conn.execute("""
                CREATE TABLE IF NOT EXISTS models (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    version       TEXT    NOT NULL UNIQUE,
                    created_at    TEXT    NOT NULL,
                    file_path     TEXT    NOT NULL,
                    metrics       TEXT    NOT NULL DEFAULT '{}',
                    train_size    INTEGER DEFAULT 0,
                    n_features    INTEGER DEFAULT 0,
                    positive_rate REAL    DEFAULT 0,
                    is_active     INTEGER DEFAULT 0
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_models_active ON models(is_active)"
            )

            # --- applications ---
            conn.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_version    TEXT    NOT NULL,
                    created_at       TEXT    NOT NULL,
                    bin_iin          TEXT,
                    region           TEXT,
                    akimat           TEXT,
                    direction        TEXT,
                    subsidy_type     TEXT,
                    normative        REAL,
                    amount           REAL,
                    district         TEXT,
                    score            REAL,
                    category         TEXT,
                    probability      REAL,
                    confidence       REAL    DEFAULT 1.0,
                    shap_explanation TEXT    DEFAULT '{}',
                    data_warnings    TEXT    DEFAULT '[]',
                    status           TEXT    DEFAULT 'scored'
                )
            """)
            # Миграция: добавить колонки если их нет (для существующих БД)
            try:
                conn.execute("ALTER TABLE applications ADD COLUMN confidence REAL DEFAULT 1.0")
            except Exception:
                pass
            try:
                conn.execute("ALTER TABLE applications ADD COLUMN data_warnings TEXT DEFAULT '[]'")
            except Exception:
                pass
            try:
                conn.execute("ALTER TABLE applications ADD COLUMN review_required INTEGER DEFAULT 0")
            except Exception:
                pass
            try:
                conn.execute("ALTER TABLE applications ADD COLUMN data_quality TEXT DEFAULT 'complete'")
            except Exception:
                pass
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_app_score ON applications(score)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_app_category ON applications(category)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_app_region ON applications(region)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_app_model ON applications(model_version)"
            )

        logger.info(f"SQLite схема инициализирована: {self.db_path}")