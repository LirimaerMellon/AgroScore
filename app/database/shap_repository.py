"""
Репозиторий для таблицы shap_results.
Хранение и извлечение SHAP-объяснений для заявок.
"""

import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from app.database.connection import Database

logger = logging.getLogger(__name__)


class ShapRepository:

    def __init__(self, db: Database):
        self.db = db

    # ---- Write ----

    def save(
        self,
        object_id: int,
        model_version: str,
        score: int,
        base_value: int,
        shap_values: List[Dict[str, Any]],
    ) -> int:
        """Сохраняет SHAP-результат. Если уже есть — заменяет."""
        now = datetime.now(timezone.utc).isoformat()
        shap_json = json.dumps(shap_values, ensure_ascii=False, default=str)

        with self.db.get_connection() as conn:
            # Upsert: удалить старую запись если есть
            conn.execute(
                "DELETE FROM shap_results WHERE object_id = ? AND model_version = ?",
                (object_id, model_version),
            )
            cursor = conn.execute(
                """
                INSERT INTO shap_results
                    (object_id, model_version, score, base_value, shap_values, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (object_id, model_version, score, base_value, shap_json, now),
            )
            return cursor.lastrowid

    def save_batch(self, entries: List[Dict[str, Any]]) -> List[int]:
        """Пакетное сохранение SHAP-результатов."""
        if not entries:
            return []

        now = datetime.now(timezone.utc).isoformat()
        ids: List[int] = []

        with self.db.get_connection() as conn:
            for e in entries:
                conn.execute(
                    "DELETE FROM shap_results WHERE object_id = ? AND model_version = ?",
                    (e["object_id"], e["model_version"]),
                )
                cursor = conn.execute(
                    """
                    INSERT INTO shap_results
                        (object_id, model_version, score, base_value, shap_values, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        e["object_id"],
                        e["model_version"],
                        e["score"],
                        e["base_value"],
                        json.dumps(e["shap_values"], ensure_ascii=False, default=str),
                        now,
                    ),
                )
                ids.append(cursor.lastrowid)

        logger.debug(f"Сохранено {len(ids)} SHAP-результатов")
        return ids

    # ---- Read ----

    def get_by_application(
        self, object_id: int, model_version: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Получить SHAP для заявки. Если model_version не указан — последний."""
        with self.db.get_connection() as conn:
            if model_version:
                row = conn.execute(
                    "SELECT * FROM shap_results WHERE object_id = ? AND model_version = ?",
                    (object_id, model_version),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM shap_results WHERE object_id = ? ORDER BY created_at DESC LIMIT 1",
                    (object_id,),
                ).fetchone()

        return self._row_to_dict(row) if row else None

    # ---- Internal ----

    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        d = dict(row)
        if "shap_values" in d and isinstance(d["shap_values"], str):
            try:
                d["shap_values"] = json.loads(d["shap_values"])
            except (json.JSONDecodeError, TypeError):
                pass
        return d

