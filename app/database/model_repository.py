"""
Репозиторий для таблицы models.
CRUD-операции над реестром обученных ML-моделей.
"""

import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from app.database.connection import Database

logger = logging.getLogger(__name__)


class ModelRepository:

    def __init__(self, db: Database):
        self.db = db

    # ---- Write ----

    def create(
        self,
        version: str,
        file_path: str,
        metrics: Dict[str, Any],
        train_size: int = 0,
        n_features: int = 0,
        positive_rate: float = 0.0,
    ) -> int:
        """Создаёт запись о новой модели и делает её активной."""
        with self.db.get_connection() as conn:
            # Деактивируем все предыдущие
            conn.execute("UPDATE models SET is_active = 0")

            cursor = conn.execute(
                """
                INSERT INTO models
                    (version, created_at, file_path, metrics,
                     train_size, n_features, positive_rate, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    version,
                    datetime.now(timezone.utc).isoformat(),
                    file_path,
                    json.dumps(metrics, ensure_ascii=False, default=str),
                    train_size,
                    n_features,
                    positive_rate,
                ),
            )
            model_id = cursor.lastrowid

        logger.info(f"Модель сохранена в БД: {version} (id={model_id})")
        return model_id

    # ---- Read ----

    def get_active(self) -> Optional[Dict[str, Any]]:
        """Возвращает текущую активную модель."""
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM models WHERE is_active = 1 LIMIT 1"
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def get_by_version(self, version: str) -> Optional[Dict[str, Any]]:
        """Возвращает модель по версии."""
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM models WHERE version = ?", (version,)
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def get_all(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Список всех моделей (новые первые)."""
        with self.db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM models ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def activate(self, version: str) -> bool:
        """Сделать указанную модель активной."""
        with self.db.get_connection() as conn:
            conn.execute("UPDATE models SET is_active = 0")
            affected = conn.execute(
                "UPDATE models SET is_active = 1 WHERE version = ?",
                (version,),
            ).rowcount
        return affected > 0

    # ---- Internal ----

    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        d = dict(row)
        if "metrics" in d and isinstance(d["metrics"], str):
            try:
                d["metrics"] = json.loads(d["metrics"])
            except (json.JSONDecodeError, TypeError):
                pass
        return d

