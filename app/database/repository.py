"""
Репозиторий для error_logs.

Основные сценарии:
- Пакетная запись ошибок из cleaner (log_errors_batch)
- Получение ошибок по trace_id (фронтенд / аналитика)
- Сводная статистика по загрузке
"""

import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from uuid import uuid4

from app.database.connection import Database

logger = logging.getLogger(__name__)


class ErrorLogRepository:

    def __init__(self, db: Database):
        self.db = db

    # Helpers
    @staticmethod
    def create_trace() -> str:
        """Новый trace_id для связки ошибок одной загрузки."""
        return str(uuid4())

    # Write
    def log_error(
        self,
        trace_id: str,
        source_type: str,
        source_name: str,
        error_codes: List[str],
        error_cols: List[str],
        locator: Dict[str, Any],
        raw_payload: Dict[str, Any],
        violations: List[Dict[str, str]],
    ) -> None:
        """Запись одной ошибки."""

        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO error_logs
                    (trace_id, detected_at, source_type, source_name,
                     error_codes, error_cols, locator, raw_payload, violations)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trace_id,
                    datetime.now(timezone.utc).isoformat(),
                    source_type,
                    source_name,
                    json.dumps(error_codes, ensure_ascii=False),
                    json.dumps(error_cols, ensure_ascii=False),
                    json.dumps(locator, ensure_ascii=False),
                    json.dumps(raw_payload, ensure_ascii=False, default=str),
                    json.dumps(violations, ensure_ascii=False),
                ),
            )


    def log_errors_batch(self, entries: List[Dict[str, Any]]) -> None:
        """
        Пакетная запись ошибок (одна транзакция).
        Каждый элемент — dict с ключами:
            trace_id, source_type, source_name,
            error_codes, error_cols, locator, raw_payload, violations
        """
        if not entries:
            return

        now = datetime.now(timezone.utc).isoformat()

        rows = []
        for e in entries:
            rows.append((
                e["trace_id"],
                now,
                e["source_type"],
                e["source_name"],
                json.dumps(e["error_codes"], ensure_ascii=False),
                json.dumps(e["error_cols"], ensure_ascii=False),
                json.dumps(e["locator"], ensure_ascii=False),
                json.dumps(e["raw_payload"], ensure_ascii=False, default=str),
                json.dumps(e["violations"], ensure_ascii=False),
            ))

        with self.db.get_connection() as conn:
            conn.executemany(
                """
                INSERT INTO error_logs
                    (trace_id, detected_at, source_type, source_name,
                     error_codes, error_cols, locator, raw_payload, violations)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

        logger.debug(f"Записано {len(rows)} ошибок (trace={entries[0]['trace_id'][:8]}…)")


    # Read
    def get_filtered(
        self,
        trace_id: Optional[str] = None,
        error_code: Optional[str] = None,
        error_col: Optional[str] = None,
        source_name: Optional[str] = None,
        sort_by: str = "detected_at",
        sort_dir: str = "desc",
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Универсальное получение ошибок с фильтрами и сортировкой."""
        conditions: List[str] = []
        params: List[Any] = []

        if trace_id:
            conditions.append("trace_id = ?")
            params.append(trace_id)
        if error_code:
            conditions.append("error_codes LIKE ?")
            params.append(f"%{error_code}%")
        if error_col:
            conditions.append("error_cols LIKE ?")
            params.append(f"%{error_col}%")
        if source_name:
            conditions.append("source_name LIKE ? COLLATE NOCASE")
            params.append(f"%{source_name}%")

        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)

        allowed_sort = {"id", "detected_at"}
        sort_col = sort_by if sort_by in allowed_sort else "detected_at"
        direction = "ASC" if sort_dir.lower() == "asc" else "DESC"

        with self.db.get_connection() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) AS cnt FROM error_logs {where}", params
            ).fetchone()["cnt"]

            rows = conn.execute(
                f"SELECT * FROM error_logs {where} "
                f"ORDER BY {sort_col} {direction} LIMIT ? OFFSET ?",
                params + [limit, offset],
            ).fetchall()

        return {"total": total, "items": [self._row_to_dict(r) for r in rows]}

    def get_by_trace(self, trace_id: str, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Ошибки одной загрузки (с пагинацией)."""
        with self.db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM error_logs WHERE trace_id = ? ORDER BY id LIMIT ? OFFSET ?",
                (trace_id, limit, offset),
            ).fetchall()

        return [self._row_to_dict(r) for r in rows]

    def get_all(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Постраничное получение всех ошибок."""
        with self.db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM error_logs ORDER BY detected_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()

        return [self._row_to_dict(r) for r in rows]

    def count(self, trace_id: Optional[str] = None) -> int:
        """Общее количество ошибок (для пагинации)."""
        with self.db.get_connection() as conn:
            if trace_id:
                row = conn.execute(
                    "SELECT COUNT(*) AS cnt FROM error_logs WHERE trace_id = ?",
                    (trace_id,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT COUNT(*) AS cnt FROM error_logs",
                ).fetchone()
        return row["cnt"] if row else 0

    def get_traces(self, limit: int = 50) -> List[Dict]:
        """Список уникальных загрузок с числом ошибок."""
        with self.db.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT trace_id,
                       source_name,
                       source_type,
                       MIN(detected_at) AS first_detected,
                       COUNT(*)         AS error_count
                FROM error_logs
                GROUP BY trace_id
                ORDER BY first_detected DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [dict(r) for r in rows]


    def get_summary(self, trace_id: Optional[str] = None) -> Dict[str, Any]:
        """Сводка: сколько ошибок, какие коды, какие колонки."""
        with self.db.get_connection() as conn:
            if trace_id:
                rows = conn.execute(
                    "SELECT error_codes, error_cols FROM error_logs WHERE trace_id = ?",
                    (trace_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT error_codes, error_cols FROM error_logs"
                ).fetchall()

        total = len(rows)
        code_counts: Dict[str, int] = {}
        col_counts: Dict[str, int] = {}

        for r in rows:
            for code in json.loads(r["error_codes"]):
                code_counts[code] = code_counts.get(code, 0) + 1
            for col in json.loads(r["error_cols"]):
                col_counts[col] = col_counts.get(col, 0) + 1

        return {
            "total_errors": total,
            "by_error_code": code_counts,
            "by_column": col_counts,
        }


    # Internal
    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        d = dict(row)
        for key in ("error_codes", "error_cols", "locator", "raw_payload", "violations"):
            if key in d and isinstance(d[key], str):
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d