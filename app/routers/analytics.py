"""
GET /api/analytics/summary       — сводная статистика
GET /api/analytics/distribution  — гистограмма скоров
GET /api/analytics/features      — важность признаков
GET /api/analytics/fairness      — fairness-отчёт (disparate impact)
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from app.database import ApplicationRepository, ModelRepository
from app.pipeline.model import ScoringModel
from app.config import FEATURE_DISPLAY_NAMES, MERGE_FEATURES

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _app_repo():
    from app.main import get_db

    return ApplicationRepository(get_db())


def _model_repo():
    from app.main import get_db

    return ModelRepository(get_db())


@router.get("/summary")
def analytics_summary(model_version: Optional[str] = Query(None, description="Фильтр по версии модели")):
    """Агрегированная статистика по всем оценённым заявкам."""
    return _app_repo().get_summary(model_version=model_version)


@router.get("/by-month")
def analytics_by_month(
    year: Optional[int] = Query(None, description="Фильтр по году"),
    model_version: Optional[str] = Query(None, description="Фильтр по версии модели"),
):
    """Количество заявок по месяцам."""
    return {"months": _app_repo().get_by_month(year=year, model_version=model_version)}


@router.get("/avg-score-by-region")
def analytics_avg_score_by_region(
    year: Optional[int] = Query(None, description="Фильтр по году"),
    model_version: Optional[str] = Query(None, description="Фильтр по версии модели"),
):
    """Средний балл по регионам."""
    return {"regions": _app_repo().get_avg_score_by_region(year=year, model_version=model_version)}


@router.get("/avg-score-by-direction")
def analytics_avg_score_by_direction(
    year: Optional[int] = Query(None, description="Фильтр по году"),
    model_version: Optional[str] = Query(None, description="Фильтр по версии модели"),
):
    """Средний балл по направлениям."""
    return {"directions": _app_repo().get_avg_score_by_direction(year=year, model_version=model_version)}


@router.get("/available-years")
def analytics_available_years():
    """Список доступных годов из данных."""
    return {"years": _app_repo().get_available_years()}


@router.get("/distribution")
def score_distribution(
    bins: int = Query(10, ge=2, le=100),
    model_version: Optional[str] = Query(None, description="Фильтр по версии модели"),
):
    """Гистограмма: количество заявок по диапазонам score (0-100)."""
    return {"bins": _app_repo().get_score_distribution(bins, model_version=model_version)}


@router.get("/features")
def feature_importance(model_version: Optional[str] = Query(None, description="Версия модели")):
    """Важность признаков из указанной или активной модели."""
    repo = _model_repo()
    if model_version:
        model_info = repo.get_by_version(model_version)
        if not model_info:
            raise HTTPException(404, f"Модель {model_version} не найдена")
    else:
        model_info = repo.get_active()
    if not model_info:
        raise HTTPException(409, "Нет обученной модели. Обучите модель, загрузив исторические данные.")

    model = ScoringModel()
    model.load(model_info["file_path"])
    fi = model.get_feature_importance()
    records = fi.to_dict("records")

    # Объединение amount + log_amount в один фактор
    merged: dict[str, float] = {}
    non_merged = []
    for r in records:
        feat = r["feature"]
        if feat in MERGE_FEATURES:
            key = MERGE_FEATURES[feat]
            merged[key] = merged.get(key, 0.0) + r["importance"]
        else:
            display = FEATURE_DISPLAY_NAMES.get(feat, feat)
            non_merged.append({"feature": display, "importance": r["importance"]})

    for key, imp in merged.items():
        non_merged.append({"feature": key, "importance": imp})

    non_merged.sort(key=lambda x: x["importance"], reverse=True)

    return {
        "model_version": model_info["version"],
        "features": non_merged,
    }


@router.get("/fairness")
def fairness_report():
    """Fairness-отчёт: распределение скоров по регионам / типам субсидий."""
    return _app_repo().get_fairness()
