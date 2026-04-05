"""
CRUD для порогов категорий и бюджета раунда.

Эндпоинты:
  GET    /api/thresholds           — текущие пороги
  PUT    /api/thresholds           — обновить пороги
  POST   /api/thresholds/reset     — сброс к дефолтным
  POST   /api/thresholds/preview   — предпросмотр (сколько заявок в каждой категории)
  GET    /api/round-budget         — текущий бюджет раунда
  PUT    /api/round-budget         — обновить бюджет раунда
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from app.schemas import (
    ThresholdUpdateRequest, ThresholdPreviewRequest,
    ThresholdPreviewResponse, RoundBudgetUpdateRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["thresholds"])


def _repo():
    from app.main import get_db
    from app.database.threshold_repository import ThresholdRepository
    return ThresholdRepository(get_db())


# ---- Thresholds ----

@router.get("/thresholds")
def get_thresholds(model_version: Optional[str] = Query(None)):
    """Текущие пороги категорий."""
    repo = _repo()
    thresholds = repo.get_thresholds(model_version)
    return {"model_version": model_version or "_default", "thresholds": thresholds}


@router.put("/thresholds")
def update_thresholds(request: ThresholdUpdateRequest):
    """Обновить пороги категорий."""
    repo = _repo()

    # Валидация: должны быть ровно 3 категории
    categories = {t.category for t in request.thresholds}
    if categories != {"LOW", "MEDIUM", "HIGH"}:
        raise HTTPException(422, "Необходимо указать ровно 3 категории: LOW, MEDIUM, HIGH")

    # Валидация: непрерывное покрытие 0–100
    sorted_t = sorted(request.thresholds, key=lambda t: t.min_score)
    if sorted_t[0].min_score != 0:
        raise HTTPException(422, "Минимальный порог должен начинаться с 0")
    if sorted_t[-1].max_score != 100:
        raise HTTPException(422, "Максимальный порог должен заканчиваться на 100")
    for i in range(len(sorted_t) - 1):
        if sorted_t[i].max_score + 1 != sorted_t[i + 1].min_score:
            raise HTTPException(
                422,
                f"Разрыв между {sorted_t[i].category} (max={sorted_t[i].max_score}) "
                f"и {sorted_t[i + 1].category} (min={sorted_t[i + 1].min_score})"
            )

    for t in sorted_t:
        if t.min_score > t.max_score:
            raise HTTPException(422, f"min_score > max_score для {t.category}")

    thresholds_dict = [t.model_dump() for t in request.thresholds]
    repo.upsert_thresholds(
        thresholds_dict,
        model_version=request.model_version or "_default",
        updated_by=request.updated_by or "admin",
    )
    return {"status": "ok", "thresholds": thresholds_dict}


@router.post("/thresholds/reset")
def reset_thresholds(
    model_version: Optional[str] = Query("_default"),
    updated_by: Optional[str] = Query("admin"),
):
    """Сброс порогов к дефолтным."""
    repo = _repo()
    repo.reset_to_defaults(model_version, updated_by)
    return {"status": "ok", "thresholds": repo.get_thresholds(model_version)}


@router.post("/thresholds/preview")
def preview_thresholds(request: ThresholdPreviewRequest):
    """Предпросмотр: количество заявок в каждой категории для предложенных порогов."""
    repo = _repo()
    thresholds_dict = [t.model_dump() for t in request.thresholds]
    counts = repo.count_by_thresholds(thresholds_dict)
    return ThresholdPreviewResponse(counts=counts)


# ---- Round Budget ----

@router.get("/round-budget")
def get_round_budget():
    """Текущий бюджет раунда."""
    repo = _repo()
    data = repo.get_round_budget()
    return data


@router.put("/round-budget")
def update_round_budget(request: RoundBudgetUpdateRequest):
    """Обновить бюджет раунда."""
    if request.budget < 0:
        raise HTTPException(422, "Бюджет не может быть отрицательным")
    repo = _repo()
    repo.set_round_budget(request.budget, request.updated_by or "admin")
    return {"status": "ok", "budget": request.budget}

