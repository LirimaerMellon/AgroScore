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

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _app_repo():
    from app.main import get_db

    return ApplicationRepository(get_db())


def _model_repo():
    from app.main import get_db

    return ModelRepository(get_db())


@router.get("/summary")
def analytics_summary():
    """Агрегированная статистика по всем оценённым заявкам."""
    return _app_repo().get_summary()


@router.get("/by-month")
def analytics_by_month(year: Optional[int] = Query(None, description="Фильтр по году")):
    """Количество заявок по месяцам."""
    return {"months": _app_repo().get_by_month(year=year)}


@router.get("/avg-score-by-region")
def analytics_avg_score_by_region(year: Optional[int] = Query(None, description="Фильтр по году")):
    """Средний балл по регионам."""
    return {"regions": _app_repo().get_avg_score_by_region(year=year)}


@router.get("/avg-score-by-direction")
def analytics_avg_score_by_direction(year: Optional[int] = Query(None, description="Фильтр по году")):
    """Средний балл по направлениям."""
    return {"directions": _app_repo().get_avg_score_by_direction(year=year)}


@router.get("/available-years")
def analytics_available_years():
    """Список доступных годов из данных."""
    return {"years": _app_repo().get_available_years()}


@router.get("/distribution")
def score_distribution(bins: int = Query(10, ge=2, le=100)):
    """Гистограмма: количество заявок по диапазонам score (0-100)."""
    return {"bins": _app_repo().get_score_distribution(bins)}


@router.get("/features")
def feature_importance():
    """Важность признаков из активной модели."""
    model_info = _model_repo().get_active()
    if not model_info:
        raise HTTPException(409, "Нет обученной модели. Обучите модель, загрузив исторические данные.")

    model = ScoringModel()
    model.load(model_info["file_path"])
    fi = model.get_feature_importance()

    return {
        "model_version": model_info["version"],
        "features": fi.to_dict("records"),
    }


@router.get("/fairness")
def fairness_report():
    """Fairness-отчёт: распределение скоров по регионам / типам субсидий."""
    return _app_repo().get_fairness()
