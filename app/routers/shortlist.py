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
    min_score: Optional[float] = Query(None, ge=0, le=100, description="Минимальный AI-балл"),
    strategy: str = Query("score", description="Стратегия отбора: score"),
):
    """
    Оптимизированный шорт-лист: выбор лучших заявок по минимальному баллу.
    Лимит бюджета считается по причитающей сумме (amount).
    """
    return _repo().get_shortlist(
        budget=budget,
        category=category,
        region=region,
        direction=direction,
        subsidy_type=subsidy_type,
        min_score=min_score,
        strategy=strategy,
    )

