"""
GET /api/shortlist — оптимизированный шорт-лист заявок в рамках бюджета.

Логика распределения субсидий (РК):
- Причитающаяся сумма (amount) = стоимость одобрения заявки для бюджета
- Заявки ранжируются по AI-баллу (merit-based)
- Комиссия задаёт лимит бюджета
- Система выбирает лучшие заявки, укладывающиеся в бюджет
- Заявки с review_required помечаются для дополнительной проверки
"""

from fastapi import APIRouter, Query
from typing import Optional
import logging

from app.database import ApplicationRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["shortlist"])


def _repo():
    from app.main import get_db
    return ApplicationRepository(get_db())


@router.get("/shortlist")
def get_shortlist(
    budget: Optional[float] = Query(None, description="Лимит бюджета (₸). Если не указан — без ограничения"),
    category: Optional[str] = Query(None, description="Фильтр по категории (HIGH/MEDIUM/LOW)"),
    region: Optional[str] = Query(None, description="Фильтр по региону"),
    direction: Optional[str] = Query(None, description="Фильтр по направлению"),
    subsidy_type: Optional[str] = Query(None, description="Фильтр по виду субсидии"),
    district: Optional[str] = Query(None, description="Фильтр по району"),
    model_version: Optional[str] = Query(None, description="Фильтр по версии модели"),
    min_score: Optional[float] = Query(None, ge=0, le=100, description="Минимальный AI-балл"),
    strategy: str = Query("more_applications", description="Стратегия при равном балле: more_applications | more_budget"),
):
    """
    Оптимизированный шорт-лист: выбор лучших заявок по минимальному баллу.
    Лимит бюджета считается по причитающей сумме (amount).
    """
    logger.info(
        "GET /api/shortlist — model_version=%s, strategy=%s, budget=%s, "
        "region=%s, direction=%s, min_score=%s",
        model_version, strategy, budget, region, direction, min_score,
    )
    result = _repo().get_shortlist(
        budget=budget,
        category=category,
        region=region,
        direction=direction,
        subsidy_type=subsidy_type,
        district=district,
        model_version=model_version,
        min_score=min_score,
        strategy=strategy,
    )
    logger.info(
        "Shortlist response: total_candidates=%d, selected_count=%d, total_in_db=%d",
        result.get("total_candidates", 0),
        result.get("selected_count", 0),
        result.get("total_in_db", 0),
    )
    return result


