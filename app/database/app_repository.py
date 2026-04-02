"""
Репозиторий для таблицы applications.
CRUD-операции над оценёнными заявками.
"""

import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from app.database.connection import Database

logger = logging.getLogger(__name__)


class ApplicationRepository:

    def __init__(self, db: Database):
        self.db = db

    # ---- Write ----

    def create_batch(self, applications: List[Dict[str, Any]]) -> List[int]:
        """Пакетная запись оценённых заявок. Возвращает список id."""
        if not applications:
            return []

        now = datetime.now(timezone.utc).isoformat()
        ids: List[int] = []

        with self.db.get_connection() as conn:
            for app in applications:
                shap = app.get("shap_explanation", {})
                warnings = app.get("data_warnings", [])
                cursor = conn.execute(
                    """
                    INSERT INTO applications
                        (model_version, created_at, bin_iin, region, akimat,
                         direction, subsidy_type, normative, amount, district,
                         score, category, probability, confidence,
                         review_required, data_quality,
                         shap_explanation, data_warnings, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        app.get("model_version", ""),
                        now,
                        app.get("bin_iin", ""),
                        app.get("region", ""),
                        app.get("akimat", ""),
                        app.get("direction", ""),
                        app.get("subsidy_type", ""),
                        app.get("normative", 0),
                        app.get("amount", 0),
                        app.get("district", ""),
                        app.get("score", 0),
                        app.get("category", ""),
                        app.get("probability", 0),
                        app.get("confidence", 1.0),
                        1 if app.get("review_required") else 0,
                        app.get("data_quality", "complete"),
                        json.dumps(shap, ensure_ascii=False, default=str),
                        json.dumps(warnings, ensure_ascii=False, default=str),
                        app.get("status", "scored"),
                    ),
                )
                ids.append(cursor.lastrowid)

        logger.debug(f"Записано {len(ids)} заявок в БД")
        return ids

    # ---- Read ----

    def get_by_id(self, app_id: int) -> Optional[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM applications WHERE id = ?", (app_id,)
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        region: Optional[str] = None,
        category: Optional[str] = None,
        model_version: Optional[str] = None,
        min_score: Optional[float] = None,
        max_score: Optional[float] = None,
        sort_by: str = "score",
        sort_dir: str = "desc",
        review_required: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Постраничный список заявок с фильтрами."""
        conditions: List[str] = []
        params: List[Any] = []

        if search:
            search_term = f"%{search}%"
            conditions.append(
                "(region LIKE ? COLLATE NOCASE"
                " OR akimat LIKE ? COLLATE NOCASE"
                " OR direction LIKE ? COLLATE NOCASE"
                " OR subsidy_type LIKE ? COLLATE NOCASE"
                " OR district LIKE ? COLLATE NOCASE"
                " OR bin_iin LIKE ? COLLATE NOCASE"
                " OR CAST(id AS TEXT) LIKE ?"
                " OR CAST(score AS TEXT) LIKE ?"
                " OR model_version LIKE ? COLLATE NOCASE"
                " OR category LIKE ? COLLATE NOCASE"
                " OR CAST(normative AS TEXT) LIKE ?"
                " OR CAST(amount AS TEXT) LIKE ?)"
            )
            params.extend([search_term] * 12)
        if region:
            conditions.append("region LIKE ? COLLATE NOCASE")
            params.append(f"%{region}%")
        if category:
            conditions.append("category = ?")
            params.append(category)
        if model_version:
            conditions.append("model_version = ?")
            params.append(model_version)
        if min_score is not None:
            conditions.append("score >= ?")
            params.append(min_score)
        if max_score is not None:
            conditions.append("score <= ?")
            params.append(max_score)
        if review_required is not None:
            conditions.append("review_required = ?")
            params.append(1 if review_required else 0)

        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)

        allowed_sort = {"score", "created_at", "amount", "normative", "id"}
        sort_col = sort_by if sort_by in allowed_sort else "score"
        direction = "ASC" if sort_dir.lower() == "asc" else "DESC"

        with self.db.get_connection() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) FROM applications {where}", params
            ).fetchone()[0]

            rows = conn.execute(
                f"SELECT * FROM applications {where} "
                f"ORDER BY {sort_col} {direction} LIMIT ? OFFSET ?",
                params + [limit, offset],
            ).fetchall()

        return {
            "total": total,
            "items": [self._row_to_dict(r) for r in rows],
        }

    def get_summary(self) -> Dict[str, Any]:
        """Агрегированная статистика по всем заявкам."""
        with self.db.get_connection() as conn:
            row = conn.execute("""
                SELECT
                    COUNT(*)                        AS total,
                    ROUND(AVG(score), 2)            AS mean_score,
                    ROUND(MIN(score), 2)            AS min_score,
                    ROUND(MAX(score), 2)            AS max_score,
                    COALESCE(SUM(CASE WHEN category='HIGH'   THEN 1 ELSE 0 END), 0) AS high,
                    COALESCE(SUM(CASE WHEN category='MEDIUM' THEN 1 ELSE 0 END), 0) AS medium,
                    COALESCE(SUM(CASE WHEN category='LOW'    THEN 1 ELSE 0 END), 0) AS low
                FROM applications
            """).fetchone()

        result = dict(row)
        return result

    def get_score_distribution(self, bins: int = 10) -> List[Dict[str, Any]]:
        """Гистограмма: количество заявок по диапазонам score."""
        step = 100 / bins
        distribution = []

        with self.db.get_connection() as conn:
            for i in range(bins):
                lo = round(i * step, 1)
                hi = round((i + 1) * step, 1)
                if i == bins - 1:
                    count = conn.execute(
                        "SELECT COUNT(*) FROM applications WHERE score >= ? AND score <= ?",
                        (lo, hi),
                    ).fetchone()[0]
                else:
                    count = conn.execute(
                        "SELECT COUNT(*) FROM applications WHERE score >= ? AND score < ?",
                        (lo, hi),
                    ).fetchone()[0]
                distribution.append({"range": f"{lo}-{hi}", "count": count})

        return distribution

    def get_fairness(self) -> Dict[str, Any]:
        """Средний скор по группам (region, subsidy_type, direction)."""
        report: Dict[str, Any] = {}

        with self.db.get_connection() as conn:
            for col in ("region", "subsidy_type", "direction"):
                rows = conn.execute(f"""
                    SELECT {col}        AS group_value,
                           COUNT(*)     AS cnt,
                           ROUND(AVG(score), 2) AS mean_score,
                           ROUND(MIN(score), 2) AS min_score,
                           ROUND(MAX(score), 2) AS max_score
                    FROM applications
                    WHERE {col} IS NOT NULL AND {col} != ''
                    GROUP BY {col}
                    ORDER BY mean_score DESC
                """).fetchall()

                groups = {r["group_value"]: dict(r) for r in rows}
                report[col] = groups

                if len(groups) > 1:
                    means = [g["mean_score"] for g in groups.values() if g["mean_score"]]
                    if means and min(means) > 0:
                        report[f"{col}_disparate_impact"] = round(max(means) / min(means), 3)

        return report

    # ---- Peer Comparison ----

    def get_by_month(self, year: Optional[int] = None) -> List[Dict[str, Any]]:
        """Количество заявок по месяцам."""
        with self.db.get_connection() as conn:
            if year:
                rows = conn.execute("""
                    SELECT substr(created_at, 1, 7) AS month,
                           COUNT(*)                 AS count,
                           ROUND(AVG(score), 2)     AS avg_score
                    FROM applications
                    WHERE created_at IS NOT NULL AND created_at != ''
                      AND substr(created_at, 1, 4) = ?
                    GROUP BY month
                    ORDER BY month
                """, (str(year),)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT substr(created_at, 1, 7) AS month,
                           COUNT(*)                 AS count,
                           ROUND(AVG(score), 2)     AS avg_score
                    FROM applications
                    WHERE created_at IS NOT NULL AND created_at != ''
                    GROUP BY month
                    ORDER BY month
                """).fetchall()
        return [dict(r) for r in rows]

    def get_avg_score_by_region(self, year: Optional[int] = None) -> List[Dict[str, Any]]:
        """Средний балл по регионам."""
        with self.db.get_connection() as conn:
            if year:
                rows = conn.execute("""
                    SELECT region,
                           COUNT(*)              AS count,
                           ROUND(AVG(score), 2)  AS avg_score,
                           ROUND(MIN(score), 2)  AS min_score,
                           ROUND(MAX(score), 2)  AS max_score,
                           ROUND(SUM(amount), 2) AS total_amount
                    FROM applications
                    WHERE region IS NOT NULL AND region != ''
                      AND substr(created_at, 1, 4) = ?
                    GROUP BY region
                    ORDER BY avg_score DESC
                """, (str(year),)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT region,
                           COUNT(*)              AS count,
                           ROUND(AVG(score), 2)  AS avg_score,
                           ROUND(MIN(score), 2)  AS min_score,
                           ROUND(MAX(score), 2)  AS max_score,
                           ROUND(SUM(amount), 2) AS total_amount
                    FROM applications
                    WHERE region IS NOT NULL AND region != ''
                    GROUP BY region
                    ORDER BY avg_score DESC
                """).fetchall()
        return [dict(r) for r in rows]

    def get_avg_score_by_direction(self, year: Optional[int] = None) -> List[Dict[str, Any]]:
        """Средний балл по направлениям."""
        with self.db.get_connection() as conn:
            if year:
                rows = conn.execute("""
                    SELECT direction,
                           COUNT(*)              AS count,
                           ROUND(AVG(score), 2)  AS avg_score,
                           ROUND(MIN(score), 2)  AS min_score,
                           ROUND(MAX(score), 2)  AS max_score,
                           ROUND(SUM(amount), 2) AS total_amount
                    FROM applications
                    WHERE direction IS NOT NULL AND direction != ''
                      AND substr(created_at, 1, 4) = ?
                    GROUP BY direction
                    ORDER BY avg_score DESC
                """, (str(year),)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT direction,
                           COUNT(*)              AS count,
                           ROUND(AVG(score), 2)  AS avg_score,
                           ROUND(MIN(score), 2)  AS min_score,
                           ROUND(MAX(score), 2)  AS max_score,
                           ROUND(SUM(amount), 2) AS total_amount
                    FROM applications
                    WHERE direction IS NOT NULL AND direction != ''
                    GROUP BY direction
                    ORDER BY avg_score DESC
                """).fetchall()
        return [dict(r) for r in rows]

    def get_available_years(self) -> List[int]:
        """Список доступных годов из данных."""
        with self.db.get_connection() as conn:
            rows = conn.execute("""
                SELECT DISTINCT substr(created_at, 1, 4) AS year
                FROM applications
                WHERE created_at IS NOT NULL AND created_at != ''
                ORDER BY year DESC
            """).fetchall()
        return [int(r["year"]) for r in rows if r["year"]]

    def get_shortlist(
        self,
        budget: Optional[float] = None,
        category: Optional[str] = None,
        region: Optional[str] = None,
        direction: Optional[str] = None,
        subsidy_type: Optional[str] = None,
        min_score: Optional[float] = None,
        strategy: str = "score",
    ) -> Dict[str, Any]:
        """
        Оптимизированный шорт-лист: выбор заявок по AI-баллу.
        Если budget указан — ограничиваем по причитающей сумме (amount).
        Если budget не указан — отбираем все заявки по min_score.
        """
        conditions: List[str] = ["amount > 0"]
        params: List[Any] = []

        if category:
            conditions.append("category = ?")
            params.append(category)
        if region:
            conditions.append("region LIKE ? COLLATE NOCASE")
            params.append(f"%{region}%")
        if direction:
            conditions.append("direction LIKE ? COLLATE NOCASE")
            params.append(f"%{direction}%")
        if subsidy_type:
            conditions.append("subsidy_type LIKE ? COLLATE NOCASE")
            params.append(f"%{subsidy_type}%")
        if min_score is not None:
            conditions.append("score >= ?")
            params.append(min_score)

        where = "WHERE " + " AND ".join(conditions)

        # Всегда сортируем по баллу
        order = "ORDER BY score DESC, amount ASC"

        with self.db.get_connection() as conn:
            # Общее число заявок в БД (для подсчёта «не вошли»)
            total_in_db = conn.execute("SELECT COUNT(*) FROM applications WHERE amount > 0").fetchone()[0]

            rows = conn.execute(
                f"""SELECT * FROM applications {where}
                    {order}""",
                params,
            ).fetchall()

        all_apps = [self._row_to_dict(r) for r in rows]

        selected = []
        excluded = []

        if budget is not None and budget > 0:
            # Жадный алгоритм: берём заявки пока укладываемся в бюджет
            remaining_budget = budget
            for app in all_apps:
                cost = float(app.get("amount", 0))
                if cost <= 0:
                    continue
                if cost <= remaining_budget:
                    selected.append(app)
                    remaining_budget -= cost
                else:
                    excluded.append(app)
            total_cost = budget - remaining_budget
        else:
            # Без бюджета — все заявки, прошедшие фильтр, попадают в шорт-лист
            selected = all_apps
            excluded = []
            total_cost = sum(float(a.get("amount", 0)) for a in selected)
            budget = total_cost  # Лимит = общая сумма отобранных

        review_count = sum(1 for a in selected if a.get("review_required"))

        return {
            "budget": budget or 0,
            "total_candidates": len(all_apps),
            "total_in_db": total_in_db,
            "selected_count": len(selected),
            "total_cost": round(total_cost, 2),
            "remaining_budget": round((budget or 0) - total_cost, 2),
            "review_required_count": review_count,
            "selected": selected,
            "excluded_count": len(excluded),
        }

    def get_peers(self, app_id: int, limit: int = 20) -> Dict[str, Any]:
        """
        Сравнение заявки с аналогичными (по области, направлению, виду субсидии).
        Возвращает статистику по аналогам и ближайшие заявки.
        """
        app = self.get_by_id(app_id)
        if not app:
            return {}

        with self.db.get_connection() as conn:
            # 1. Аналоги по области
            region_stats = None
            if app.get("region"):
                row = conn.execute("""
                    SELECT COUNT(*) AS cnt,
                           ROUND(AVG(score), 2) AS mean_score,
                           ROUND(MIN(score), 2) AS min_score,
                           ROUND(MAX(score), 2) AS max_score,
                           ROUND(AVG(amount), 2) AS mean_amount
                    FROM applications
                    WHERE region = ? COLLATE NOCASE AND id != ?
                """, (app["region"], app_id)).fetchone()
                if row and row["cnt"] > 0:
                    region_stats = dict(row)

            # 2. Аналоги по направлению
            direction_stats = None
            if app.get("direction"):
                row = conn.execute("""
                    SELECT COUNT(*) AS cnt,
                           ROUND(AVG(score), 2) AS mean_score,
                           ROUND(MIN(score), 2) AS min_score,
                           ROUND(MAX(score), 2) AS max_score,
                           ROUND(AVG(amount), 2) AS mean_amount
                    FROM applications
                    WHERE direction = ? COLLATE NOCASE AND id != ?
                """, (app["direction"], app_id)).fetchone()
                if row and row["cnt"] > 0:
                    direction_stats = dict(row)

            # 3. Аналоги по виду субсидии
            subsidy_stats = None
            if app.get("subsidy_type"):
                row = conn.execute("""
                    SELECT COUNT(*) AS cnt,
                           ROUND(AVG(score), 2) AS mean_score,
                           ROUND(MIN(score), 2) AS min_score,
                           ROUND(MAX(score), 2) AS max_score,
                           ROUND(AVG(amount), 2) AS mean_amount
                    FROM applications
                    WHERE subsidy_type = ? COLLATE NOCASE AND id != ?
                """, (app["subsidy_type"], app_id)).fetchone()
                if row and row["cnt"] > 0:
                    subsidy_stats = dict(row)

            # 4. Перцентиль — какой % заявок имеют балл ниже текущей
            total_count = conn.execute(
                "SELECT COUNT(*) FROM applications"
            ).fetchone()[0]
            lower_count = conn.execute(
                "SELECT COUNT(*) FROM applications WHERE score < ?",
                (app["score"],)
            ).fetchone()[0]
            percentile = round(lower_count / total_count * 100, 1) if total_count > 0 else 0

            # 5. Ближайшие заявки (по баллу) с тем же регионом
            similar_apps = []
            if app.get("region"):
                rows = conn.execute("""
                    SELECT id, score, category, region, direction, subsidy_type, amount
                    FROM applications
                    WHERE region = ? COLLATE NOCASE AND id != ?
                    ORDER BY ABS(score - ?) ASC
                    LIMIT ?
                """, (app["region"], app_id, app["score"], limit)).fetchall()
                similar_apps = [dict(r) for r in rows]

        return {
            "application_score": app["score"],
            "application_category": app["category"],
            "percentile": percentile,
            "total_applications": total_count,
            "region_stats": region_stats,
            "direction_stats": direction_stats,
            "subsidy_stats": subsidy_stats,
            "similar_apps": similar_apps[:10],
        }

    # ---- Internal ----

    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        d = dict(row)
        for json_field in ("shap_explanation", "data_warnings"):
            if json_field in d and isinstance(d[json_field], str):
                try:
                    d[json_field] = json.loads(d[json_field])
                except (json.JSONDecodeError, TypeError):
                    pass
        # Нормализация boolean-полей из SQLite (0/1 → bool)
        if "review_required" in d:
            d["review_required"] = bool(d["review_required"])
        return d

