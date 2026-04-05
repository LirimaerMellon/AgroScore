"""
Репозиторий для таблиц score_thresholds и round_settings.
Управление порогами категорий (LOW/MEDIUM/HIGH) и бюджетом раунда.
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from app.database.connection import Database

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLDS = [
    {"category": "LOW", "min_score": 0, "max_score": 39},
    {"category": "MEDIUM", "min_score": 40, "max_score": 69},
    {"category": "HIGH", "min_score": 70, "max_score": 100},
]


class ThresholdRepository:

    def __init__(self, db: Database):
        self.db = db

    # ---- Read ----

    def get_thresholds(self, model_version: Optional[str] = None) -> List[Dict[str, Any]]:
        """Получить пороги для версии модели. Если нет — дефолтные (_default)."""
        with self.db.get_connection() as conn:
            if model_version:
                rows = conn.execute(
                    "SELECT * FROM score_thresholds WHERE model_version = ? ORDER BY min_score",
                    (model_version,),
                ).fetchall()
                if rows:
                    return [dict(r) for r in rows]
            # Fallback: _default
            rows = conn.execute(
                "SELECT * FROM score_thresholds WHERE model_version = '_default' ORDER BY min_score",
            ).fetchall()
            if rows:
                return [dict(r) for r in rows]
        # Абсолютный fallback
        return [dict(t) for t in DEFAULT_THRESHOLDS]

    def get_bins_labels(self, model_version: Optional[str] = None) -> Tuple[List[float], List[str]]:
        """
        Возвращает (bins, labels) для pd.cut().
        Пример: ([0, 40, 70, 100], ['LOW', 'MEDIUM', 'HIGH'])
        """
        thresholds = self.get_thresholds(model_version)
        thresholds.sort(key=lambda t: t["min_score"])
        bins = [thresholds[0]["min_score"]]
        labels = []
        for t in thresholds:
            bins.append(t["max_score"])
            labels.append(t["category"])
        return bins, labels

    def categorize(self, score: float, model_version: Optional[str] = None) -> str:
        """Определяет категорию по баллу и текущим порогам."""
        thresholds = self.get_thresholds(model_version)
        thresholds.sort(key=lambda t: t["min_score"])
        for t in thresholds:
            if t["min_score"] <= score <= t["max_score"]:
                return t["category"]
        # Fallback
        if score <= 39:
            return "LOW"
        elif score <= 69:
            return "MEDIUM"
        return "HIGH"

    # ---- Write ----

    def upsert_thresholds(
        self,
        thresholds: List[Dict[str, Any]],
        model_version: str = "_default",
        updated_by: str = "admin",
    ) -> None:
        """Полная замена порогов для указанной версии модели."""
        now = datetime.now(timezone.utc).isoformat()
        with self.db.get_connection() as conn:
            conn.execute(
                "DELETE FROM score_thresholds WHERE model_version = ?",
                (model_version,),
            )
            for t in thresholds:
                conn.execute(
                    """INSERT INTO score_thresholds
                        (model_version, category, min_score, max_score, updated_by, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (model_version, t["category"], t["min_score"], t["max_score"],
                     updated_by, now),
                )
        logger.info(f"Пороги обновлены: model_version={model_version}, by={updated_by}")

    def reset_to_defaults(self, model_version: str = "_default", updated_by: str = "admin") -> None:
        """Сброс порогов к дефолтным."""
        self.upsert_thresholds(DEFAULT_THRESHOLDS, model_version, updated_by)

    def init_defaults(self) -> None:
        """Вставить дефолтные пороги если таблица пуста."""
        with self.db.get_connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM score_thresholds WHERE model_version = '_default'"
            ).fetchone()[0]
            if count == 0:
                now = datetime.now(timezone.utc).isoformat()
                for t in DEFAULT_THRESHOLDS:
                    conn.execute(
                        """INSERT INTO score_thresholds
                            (model_version, category, min_score, max_score, updated_by, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)""",
                        ("_default", t["category"], t["min_score"], t["max_score"],
                         "system", now),
                    )
                logger.info("Дефолтные пороги категорий инициализированы")

    # ---- Preview ----

    def count_by_thresholds(self, thresholds: List[Dict[str, Any]]) -> Dict[str, int]:
        """Предпросмотр: количество заявок в каждой категории для указанных порогов."""
        result: Dict[str, int] = {}
        with self.db.get_connection() as conn:
            for t in thresholds:
                count = conn.execute(
                    "SELECT COUNT(*) FROM applications WHERE score >= ? AND score <= ?",
                    (t["min_score"], t["max_score"]),
                ).fetchone()[0]
                result[t["category"]] = count
        return result

    # ---- Round Budget ----

    def get_round_budget(self) -> Dict[str, Any]:
        """Получить бюджет раунда."""
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT budget, updated_by, updated_at FROM round_settings WHERE id = 1"
            ).fetchone()
        if row:
            return dict(row)
        return {"budget": 0, "updated_by": None, "updated_at": None}

    def set_round_budget(self, budget: float, updated_by: str = "admin") -> None:
        """Установить бюджет раунда."""
        now = datetime.now(timezone.utc).isoformat()
        with self.db.get_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO round_settings (id, budget, updated_by, updated_at)
                VALUES (1, ?, ?, ?)""",
                (budget, updated_by, now),
            )
        logger.info(f"Бюджет раунда обновлён: {budget}, by={updated_by}")

