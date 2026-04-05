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
                unknown_fields = app.get("unknown_fields", [])
                cursor = conn.execute(
                    """
                    INSERT INTO applications
                        (model_version, created_at, bin_iin, region, akimat,
                         direction, subsidy_type, normative, amount, district,
                         score, category, probability, confidence,
                         review_required, data_quality,
                         confidence_level, unknown_fields,
                         shap_explanation, data_warnings, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        app.get("confidence_level", "HIGH"),
                        json.dumps(unknown_fields, ensure_ascii=False),
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
        confidence_level: Optional[str] = None,
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
        if confidence_level:
            conditions.append("confidence_level = ?")
            params.append(confidence_level)

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

    def get_summary(self, model_version: Optional[str] = None) -> Dict[str, Any]:
        """Агрегированная статистика по всем заявкам."""
        mv_filter = ""
        params: List[Any] = []
        if model_version:
            mv_filter = "WHERE model_version = ?"
            params.append(model_version)

        with self.db.get_connection() as conn:
            row = conn.execute(f"""
                SELECT
                    COUNT(*)                        AS total,
                    ROUND(AVG(CASE WHEN confidence_level != 'LOW' THEN score END), 2) AS mean_score,
                    ROUND(MIN(CASE WHEN confidence_level != 'LOW' THEN score END), 2) AS min_score,
                    ROUND(MAX(CASE WHEN confidence_level != 'LOW' THEN score END), 2) AS max_score,
                    COALESCE(SUM(CASE WHEN category='HIGH'   AND confidence_level != 'LOW' THEN 1 ELSE 0 END), 0) AS high,
                    COALESCE(SUM(CASE WHEN category='MEDIUM' AND confidence_level != 'LOW' THEN 1 ELSE 0 END), 0) AS medium,
                    COALESCE(SUM(CASE WHEN category='LOW'    AND confidence_level != 'LOW' THEN 1 ELSE 0 END), 0) AS low,
                    ROUND(COALESCE(SUM(amount), 0), 2) AS total_amount,
                    ROUND(COALESCE(AVG(amount), 0), 2) AS mean_amount,
                    COALESCE(SUM(CASE WHEN confidence_level = 'HIGH'   OR confidence_level IS NULL THEN 1 ELSE 0 END), 0) AS confidence_high,
                    COALESCE(SUM(CASE WHEN confidence_level = 'MEDIUM' THEN 1 ELSE 0 END), 0) AS confidence_medium,
                    COALESCE(SUM(CASE WHEN confidence_level = 'LOW'    THEN 1 ELSE 0 END), 0) AS confidence_low
                FROM applications {mv_filter}
            """, params).fetchone()

        result = dict(row)
        return result

    def get_score_distribution(self, bins: int = 10, model_version: Optional[str] = None) -> List[Dict[str, Any]]:
        """Гистограмма: количество заявок по диапазонам score."""
        step = 100 / bins
        distribution = []
        mv_filter = ""
        mv_params: List[Any] = []
        if model_version:
            mv_filter = " AND model_version = ?"
            mv_params = [model_version]

        with self.db.get_connection() as conn:
            for i in range(bins):
                lo = round(i * step, 1)
                hi = round((i + 1) * step, 1)
                if i == bins - 1:
                    count = conn.execute(
                        f"SELECT COUNT(*) FROM applications WHERE score >= ? AND score <= ?{mv_filter}",
                        [lo, hi] + mv_params,
                    ).fetchone()[0]
                else:
                    count = conn.execute(
                        f"SELECT COUNT(*) FROM applications WHERE score >= ? AND score < ?{mv_filter}",
                        [lo, hi] + mv_params,
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

    def get_by_month(self, year: Optional[int] = None, model_version: Optional[str] = None) -> List[Dict[str, Any]]:
        """Количество заявок по месяцам."""
        conditions = ["created_at IS NOT NULL AND created_at != ''"]
        params: List[Any] = []
        if year:
            conditions.append("substr(created_at, 1, 4) = ?")
            params.append(str(year))
        if model_version:
            conditions.append("model_version = ?")
            params.append(model_version)
        where = "WHERE " + " AND ".join(conditions)

        with self.db.get_connection() as conn:
            rows = conn.execute(f"""
                SELECT substr(created_at, 1, 7) AS month,
                       COUNT(*)                 AS count,
                       ROUND(AVG(score), 2)     AS avg_score
                FROM applications
                {where}
                GROUP BY month
                ORDER BY month
            """, params).fetchall()
        return [dict(r) for r in rows]

    def get_avg_score_by_region(self, year: Optional[int] = None, model_version: Optional[str] = None) -> List[Dict[str, Any]]:
        """Средний балл по регионам."""
        conditions = ["region IS NOT NULL AND region != ''"]
        params: List[Any] = []
        if year:
            conditions.append("substr(created_at, 1, 4) = ?")
            params.append(str(year))
        if model_version:
            conditions.append("model_version = ?")
            params.append(model_version)
        where = "WHERE " + " AND ".join(conditions)

        with self.db.get_connection() as conn:
            rows = conn.execute(f"""
                SELECT region,
                       COUNT(*)              AS count,
                       ROUND(AVG(score), 2)  AS avg_score,
                       ROUND(MIN(score), 2)  AS min_score,
                       ROUND(MAX(score), 2)  AS max_score,
                       ROUND(SUM(amount), 2) AS total_amount
                FROM applications
                {where}
                GROUP BY region
                ORDER BY avg_score DESC
            """, params).fetchall()
        return [dict(r) for r in rows]

    def get_avg_score_by_direction(self, year: Optional[int] = None, model_version: Optional[str] = None) -> List[Dict[str, Any]]:
        """Средний балл по направлениям."""
        conditions = ["direction IS NOT NULL AND direction != ''"]
        params: List[Any] = []
        if year:
            conditions.append("substr(created_at, 1, 4) = ?")
            params.append(str(year))
        if model_version:
            conditions.append("model_version = ?")
            params.append(model_version)
        where = "WHERE " + " AND ".join(conditions)

        with self.db.get_connection() as conn:
            rows = conn.execute(f"""
                SELECT direction,
                       COUNT(*)              AS count,
                       ROUND(AVG(score), 2)  AS avg_score,
                       ROUND(MIN(score), 2)  AS min_score,
                       ROUND(MAX(score), 2)  AS max_score,
                       ROUND(SUM(amount), 2) AS total_amount
                FROM applications
                {where}
                GROUP BY direction
                ORDER BY avg_score DESC
            """, params).fetchall()
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

    # Колонки, необходимые для шорт-листа (без тяжёлых JSON-полей)
    _SHORTLIST_COLS = (
        "id, model_version, bin_iin, region, akimat, direction, subsidy_type,"
        " normative, amount, district, score, category, probability, confidence,"
        " review_required, data_quality, confidence_level, created_at"
    )

    def get_shortlist(
        self,
        budget: Optional[float] = None,
        category: Optional[str] = None,
        region: Optional[str] = None,
        direction: Optional[str] = None,
        subsidy_type: Optional[str] = None,
        district: Optional[str] = None,
        model_version: Optional[str] = None,
        min_score: Optional[float] = None,
        strategy: str = "more_applications",
    ) -> Dict[str, Any]:
        """
        Шорт-лист: все заявки отсортированные по баллу с рангом,
        накопительной суммой и флагом fits_budget.
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
        if district:
            conditions.append("district LIKE ? COLLATE NOCASE")
            params.append(f"%{district}%")
        if model_version:
            conditions.append("model_version = ?")
            params.append(model_version)
        if min_score is not None:
            conditions.append("score >= ?")
            params.append(min_score)

        where = "WHERE " + " AND ".join(conditions)

        # Стратегия определяет порядок при равном балле
        if strategy == "more_budget":
            order = "ORDER BY score DESC, amount DESC"
        else:
            # "more_applications" — при равном балле дешёвые первыми → больше заявок
            order = "ORDER BY score DESC, amount ASC"

        with self.db.get_connection() as conn:
            # Общее число заявок в БД с учётом модели (для подсчёта «не вошли»)
            if model_version:
                total_in_db = conn.execute(
                    "SELECT COUNT(*) FROM applications WHERE amount > 0 AND model_version = ?",
                    (model_version,),
                ).fetchone()[0]
            else:
                total_in_db = conn.execute(
                    "SELECT COUNT(*) FROM applications WHERE amount > 0"
                ).fetchone()[0]

            rows = conn.execute(
                f"""SELECT {self._SHORTLIST_COLS} FROM applications {where}
                    {order}""",
                params,
            ).fetchall()

        all_apps = [self._shortlist_row_to_dict(r) for r in rows]

        # Проставляем rank, cumulative_sum, fits_budget
        cumulative = 0.0
        selected = []
        excluded = []

        for i, app in enumerate(all_apps):
            cost = float(app.get("amount", 0))
            cumulative += cost
            app["rank"] = i + 1
            app["cumulative_sum"] = round(cumulative, 2)

            if budget is not None and budget > 0:
                app["fits_budget"] = cumulative <= budget
            else:
                app["fits_budget"] = True

        if budget is not None and budget > 0:
            for app in all_apps:
                if app["fits_budget"]:
                    selected.append(app)
                else:
                    excluded.append(app)
            total_cost = sum(float(a.get("amount", 0)) for a in selected)
        else:
            selected = all_apps
            excluded = []
            total_cost = cumulative
            budget = total_cost

        review_count = sum(1 for a in selected if a.get("review_required"))

        return {
            "budget": budget or 0,
            "total_candidates": len(all_apps),
            "total_in_db": total_in_db,
            "selected_count": len(selected),
            "total_cost": round(total_cost, 2),
            "remaining_budget": round((budget or 0) - total_cost, 2),
            "review_required_count": review_count,
            "selected": all_apps,  # Все заявки (с rank, cumulative_sum, fits_budget)
            "excluded_count": len(excluded),
        }

    # ---- Rank & Budget ----

    def get_rank(self, app_id: int) -> int:
        """Ранг заявки среди всех (1-based, по score DESC)."""
        with self.db.get_connection() as conn:
            app = conn.execute(
                "SELECT score FROM applications WHERE id = ?", (app_id,)
            ).fetchone()
            if not app:
                return 0
            rank = conn.execute(
                "SELECT COUNT(*) + 1 FROM applications WHERE score > ?",
                (app["score"],),
            ).fetchone()[0]
        return rank

    def get_fits_budget(self, app_id: int, budget: float) -> bool:
        """Проверяет, укладывается ли заявка в бюджет по рангу."""
        with self.db.get_connection() as conn:
            app = conn.execute(
                "SELECT score, amount FROM applications WHERE id = ?", (app_id,)
            ).fetchone()
            if not app:
                return False
            # Сумма amount всех заявок с более высоким баллом
            cumulative = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM applications WHERE score > ? AND amount > 0",
                (app["score"],),
            ).fetchone()[0]
            cumulative += float(app["amount"] or 0)
        return cumulative <= budget

    # ---- Peer Comparison ----

    def get_peers(self, app_id: int, limit: int = 20) -> Dict[str, Any]:
        """
        Сравнение заявки с аналогичными (по области, направлению, виду субсидии).
        Возвращает статистику по аналогам и ближайшие заявки.
        """
        app = self.get_by_id(app_id)
        if not app:
            return {}

        def _group_stats(conn, col: str, val: str, app_id: int) -> Optional[Dict[str, Any]]:
            """Унифицированная статистика по группе аналогов."""
            row = conn.execute(f"""
                SELECT COUNT(*) AS cnt,
                       ROUND(AVG(score), 2)    AS mean_score,
                       ROUND(MIN(score), 2)    AS min_score,
                       ROUND(MAX(score), 2)    AS max_score,
                       ROUND(AVG(amount), 2)   AS mean_amount,
                       ROUND(MIN(amount), 2)   AS min_amount,
                       ROUND(MAX(amount), 2)   AS max_amount,
                       ROUND(SUM(amount), 2)   AS total_amount,
                       COALESCE(SUM(CASE WHEN category='HIGH'   THEN 1 ELSE 0 END), 0) AS high_count,
                       COALESCE(SUM(CASE WHEN category='MEDIUM' THEN 1 ELSE 0 END), 0) AS medium_count,
                       COALESCE(SUM(CASE WHEN category='LOW'    THEN 1 ELSE 0 END), 0) AS low_count
                FROM applications
                WHERE {col} = ? COLLATE NOCASE AND id != ?
            """, (val, app_id)).fetchone()
            if row and row["cnt"] > 0:
                return dict(row)
            return None

        with self.db.get_connection() as conn:
            # 1. Аналоги по области
            region_stats = _group_stats(conn, "region", app.get("region", ""), app_id) if app.get("region") else None

            # 2. Аналоги по направлению
            direction_stats = _group_stats(conn, "direction", app.get("direction", ""), app_id) if app.get("direction") else None

            # 3. Аналоги по виду субсидии
            subsidy_stats = _group_stats(conn, "subsidy_type", app.get("subsidy_type", ""), app_id) if app.get("subsidy_type") else None

            # 4. Аналоги по району
            district_stats = _group_stats(conn, "district", app.get("district", ""), app_id) if app.get("district") else None

            # 5. Глобальная статистика (все заявки кроме текущей)
            global_row = conn.execute("""
                SELECT COUNT(*) AS cnt,
                       ROUND(AVG(score), 2)    AS mean_score,
                       ROUND(MIN(score), 2)    AS min_score,
                       ROUND(MAX(score), 2)    AS max_score,
                       ROUND(AVG(amount), 2)   AS mean_amount,
                       ROUND(SUM(amount), 2)   AS total_amount,
                       COALESCE(SUM(CASE WHEN category='HIGH'   THEN 1 ELSE 0 END), 0) AS high_count,
                       COALESCE(SUM(CASE WHEN category='MEDIUM' THEN 1 ELSE 0 END), 0) AS medium_count,
                       COALESCE(SUM(CASE WHEN category='LOW'    THEN 1 ELSE 0 END), 0) AS low_count
                FROM applications WHERE id != ?
            """, (app_id,)).fetchone()
            global_stats = dict(global_row) if global_row and global_row["cnt"] > 0 else None

            # 6. Перцентиль — какой % заявок имеют балл ниже текущей
            total_count = conn.execute(
                "SELECT COUNT(*) FROM applications"
            ).fetchone()[0]
            lower_count = conn.execute(
                "SELECT COUNT(*) FROM applications WHERE score < ?",
                (app["score"],)
            ).fetchone()[0]
            percentile = round(lower_count / total_count * 100, 1) if total_count > 0 else 0

            # 7. Ранг по сумме среди аналогов по области
            amount_rank_region = None
            if app.get("region") and app.get("amount") is not None:
                rank_row = conn.execute("""
                    SELECT COUNT(*) + 1 AS rank
                    FROM applications
                    WHERE region = ? COLLATE NOCASE AND id != ? AND amount > ?
                """, (app["region"], app_id, app["amount"])).fetchone()
                if rank_row:
                    amount_rank_region = rank_row["rank"]

            # 8. Аналоги по диапазону суммы (±30% от суммы текущей заявки)
            amount_range_stats = None
            app_amount = float(app.get("amount", 0))
            if app_amount > 0:
                lo_amount = app_amount * 0.7
                hi_amount = app_amount * 1.3
                row = conn.execute("""
                    SELECT COUNT(*) AS cnt,
                           ROUND(AVG(score), 2)  AS mean_score,
                           ROUND(MIN(score), 2)  AS min_score,
                           ROUND(MAX(score), 2)  AS max_score,
                           ROUND(AVG(amount), 2) AS mean_amount
                    FROM applications
                    WHERE amount >= ? AND amount <= ? AND id != ?
                """, (lo_amount, hi_amount, app_id)).fetchone()
                if row and row["cnt"] > 0:
                    amount_range_stats = dict(row)
                    amount_range_stats["range_from"] = round(lo_amount, 2)
                    amount_range_stats["range_to"] = round(hi_amount, 2)

            # 9. Ближайшие заявки (по баллу) с тем же регионом
            similar_apps = []
            if app.get("region"):
                rows = conn.execute("""
                    SELECT id, score, category, region, direction, subsidy_type, amount, bin_iin
                    FROM applications
                    WHERE region = ? COLLATE NOCASE AND id != ?
                    ORDER BY ABS(score - ?) ASC
                    LIMIT ?
                """, (app["region"], app_id, app["score"], limit)).fetchall()
                similar_apps = [dict(r) for r in rows]

        return {
            "application_score": app["score"],
            "application_category": app["category"],
            "application_amount": app.get("amount", 0),
            "percentile": percentile,
            "total_applications": total_count,
            "amount_rank_region": amount_rank_region,
            "region_stats": region_stats,
            "direction_stats": direction_stats,
            "subsidy_stats": subsidy_stats,
            "district_stats": district_stats,
            "global_stats": global_stats,
            "amount_range_stats": amount_range_stats,
            "similar_apps": similar_apps[:10],
        }

    # ---- Internal ----

    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        d = dict(row)
        for json_field in ("shap_explanation", "data_warnings", "unknown_fields"):
            if json_field in d and isinstance(d[json_field], str):
                try:
                    d[json_field] = json.loads(d[json_field])
                except (json.JSONDecodeError, TypeError):
                    pass
        # Нормализация boolean-полей из SQLite (0/1 → bool)
        if "review_required" in d:
            d["review_required"] = bool(d["review_required"])
        # Fallback для старых записей без confidence_level
        if "confidence_level" not in d or not d.get("confidence_level"):
            d["confidence_level"] = "HIGH"
        if "unknown_fields" not in d or not d.get("unknown_fields"):
            d["unknown_fields"] = []
        return d

    @staticmethod
    def _shortlist_row_to_dict(row) -> Dict[str, Any]:
        """Облегчённый _row_to_dict для шорт-листа: исключает тяжёлые JSON-поля."""
        d = dict(row)
        # Удалить тяжёлые поля, если они случайно попали в SELECT
        for heavy in ("shap_explanation", "data_warnings", "unknown_fields"):
            d.pop(heavy, None)
        if "review_required" in d:
            d["review_required"] = bool(d["review_required"])
        if "confidence_level" not in d or not d.get("confidence_level"):
            d["confidence_level"] = "HIGH"
        return d

