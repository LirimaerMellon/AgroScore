"""
GET /api/applications       — список оценённых заявок (с фильтрами и пагинацией)
GET /api/applications/{id}  — детали заявки с SHAP-объяснением
GET /api/applications/{id}/analysis — риски, сравнение с аналогами, перцентиль
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from app.database import ApplicationRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["applications"])


def _repo():
    from app.main import get_db
    return ApplicationRepository(get_db())


@router.get("/applications")
def list_applications(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    region: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    model_version: Optional[str] = Query(None),
    min_score: Optional[float] = Query(None, ge=0, le=100),
    max_score: Optional[float] = Query(None, ge=0, le=100),
    sort_by: str = Query("score", description="score|created_at|amount|normative"),
    sort_dir: str = Query("desc", description="asc|desc"),
    review_required: Optional[bool] = Query(None),
    search: Optional[str] = Query(None, description="Универсальный поиск по всем полям"),
):
    """Постраничный список оценённых заявок с фильтрами."""
    return _repo().get_all(
        limit=limit,
        offset=offset,
        region=region,
        category=category,
        model_version=model_version,
        min_score=min_score,
        max_score=max_score,
        sort_by=sort_by,
        sort_dir=sort_dir,
        review_required=review_required,
        search=search,
    )


@router.get("/applications/{app_id}")
def get_application(app_id: int):
    """Детали заявки с полным SHAP-объяснением."""
    app = _repo().get_by_id(app_id)
    if not app:
        raise HTTPException(404, f"Заявка {app_id} не найдена")
    return {"application": app}


@router.get("/applications/{app_id}/analysis")
def get_application_analysis(app_id: int):
    """
    Расширенный анализ заявки:
    - Риски (на основе отрицательных SHAP-факторов)
    - Сравнение с аналогами (по области, направлению, виду субсидии)
    - Перцентиль (позиция среди всех заявок)
    """
    repo = _repo()

    app = repo.get_by_id(app_id)
    if not app:
        raise HTTPException(404, f"Заявка {app_id} не найдена")

    # Peer comparison
    peers = repo.get_peers(app_id, limit=10)

    # Risk assessment на основе SHAP
    shap_data = app.get("shap_explanation", {})
    risks = []
    score_interpretation = ""

    if isinstance(shap_data, dict):
        # Используем risk_factors если есть, иначе фильтруем top_factors
        risk_factors = shap_data.get("risk_factors", [])
        if not risk_factors:
            all_factors = shap_data.get("top_factors", [])
            risk_factors = [f for f in all_factors if f.get("direction") == "negative"]

        for rf in risk_factors:
            impact_val = abs(rf.get("shap_value", rf.get("importance", 0)))
            severity = "high" if impact_val > 0.5 else \
                       "medium" if impact_val > 0.1 else "low"
            display = rf.get("display_name", rf.get("feature", ""))
            # Формируем текстовое описание риска
            if severity == "high":
                description = f"Фактор «{display}» оказывает сильное отрицательное влияние на оценку (вклад: {-impact_val:.4f}). Рекомендуется детальная проверка."
            elif severity == "medium":
                description = f"Фактор «{display}» умеренно снижает оценку (вклад: {-impact_val:.4f}). Обратите внимание при рассмотрении."
            else:
                description = f"Фактор «{display}» незначительно влияет на снижение оценки (вклад: {-impact_val:.4f})."
            risks.append({
                "feature": rf.get("feature", ""),
                "display_name": display,
                "impact": round(rf.get("shap_value", -rf.get("importance", 0)), 6),
                "severity": severity,
                "description": description,
            })

        # Текстовая интерпретация
        score = app.get("score", 0)
        category = app.get("category", "")

        positive_factors = shap_data.get("positive_factors", [])
        if not positive_factors:
            all_factors = shap_data.get("top_factors", [])
            positive_factors = [f for f in all_factors if f.get("direction") == "positive"]

        if score >= 70:
            score_interpretation = (
                f"Заявка получила высокий балл ({score:.0f}/100). "
                f"Основные положительные факторы: "
                + ", ".join(f.get("display_name", f.get("feature", "")) for f in positive_factors[:3])
                + "." if positive_factors else
                f"Заявка получила высокий балл ({score:.0f}/100)."
            )
        elif score >= 40:
            score_interpretation = (
                f"Заявка получила средний балл ({score:.0f}/100). "
                f"Имеются как положительные, так и отрицательные факторы."
            )
        else:
            score_interpretation = (
                f"Заявка получила низкий балл ({score:.0f}/100). "
                f"Основные факторы риска: "
                + ", ".join(f.get("display_name", f.get("feature", "")) for f in risk_factors[:3])
                + "." if risk_factors else
                f"Заявка получила низкий балл ({score:.0f}/100)."
            )

    return {
        "app_id": app_id,
        "score": app.get("score", 0),
        "category": app.get("category", ""),
        "score_interpretation": score_interpretation,
        "risks": risks,
        "peers": peers,
    }

