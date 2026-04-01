"""
Менеджер подключений к SQLite.

- Создаёт файл БД и родительские папки автоматически
- WAL-режим для параллельного чтения
- Context manager для безопасных транзакций
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
                "CREATE INDEX IF NOT EXISTS idx_el_trace "
                "ON error_logs(trace_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_el_source "
                "ON error_logs(source_name)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_el_detected "
                "ON error_logs(detected_at)"
            )

        logger.info(f"SQLite схема инициализирована: {self.db_path}")