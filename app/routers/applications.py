"""
GET /api/applications       — список оценённых заявок (с фильтрами и пагинацией)
GET /api/applications/{id}  — детали заявки с SHAP-объяснением
GET /api/applications/{id}/analysis — риски, сравнение с аналогами, перцентиль
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
import logging

from app.database import ApplicationRepository, ShapRepository, ThresholdRepository
from app.config import CATEGORY_DISPLAY, FEATURE_DISPLAY_NAMES, MERGE_FEATURES

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["applications"])


def _repo():
    from app.main import get_db
    return ApplicationRepository(get_db())


def _shap_repo():
    from app.main import get_db
    return ShapRepository(get_db())


def _threshold_repo():
    from app.main import get_db
    return ThresholdRepository(get_db())


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
    confidence_level: Optional[str] = Query(None, description="HIGH|MEDIUM|LOW"),
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
        confidence_level=confidence_level,
    )


@router.get("/applications/{app_id}")
def get_application(app_id: int):
    """Детали заявки с полным SHAP-объяснением."""
    app = _repo().get_by_id(app_id)
    if not app:
        raise HTTPException(404, f"Заявка {app_id} не найдена")
    return {"application": app}


def _build_narrative(app: Dict[str, Any], shap_data: Dict[str, Any], peers: Dict[str, Any]) -> str:
    """
    Генерирует развёрнутое текстовое описание решения по заявке.
    Человекочитаемое объяснение: почему модель поставила такой балл,
    что хорошо, что плохо, как заявка соотносится с аналогами.
    """
    score = app.get("score", 0)
    category = app.get("category", "")
    region = app.get("region", "—")
    direction = app.get("direction", "—")
    subsidy_type = app.get("subsidy_type", "—")
    amount = app.get("amount", 0)
    normative = app.get("normative", 0)

    lines: List[str] = []

    # 1. Общая оценка
    if score >= 70:
        lines.append(
            f"Заявка #{app.get('id', '?')} получила высокий AI-балл: {score:.0f} из 100 (категория {category}). "
            f"Это свидетельствует о высокой вероятности соответствия критериям одобрения."
        )
    elif score >= 40:
        lines.append(
            f"Заявка #{app.get('id', '?')} получила средний AI-балл: {score:.0f} из 100 (категория {category}). "
            f"Имеются как положительные, так и отрицательные факторы. Рекомендуется дополнительное рассмотрение комиссией."
        )
    else:
        lines.append(
            f"Заявка #{app.get('id', '?')} получила низкий AI-балл: {score:.0f} из 100 (категория {category}). "
            f"Модель выявила значительные факторы риска, снижающие вероятность одобрения."
        )

    # 2. Положительные факторы
    positive_factors = shap_data.get("positive_factors", [])
    if not positive_factors:
        all_factors = shap_data.get("top_factors", [])
        positive_factors = [f for f in all_factors if f.get("direction") == "positive"]

    if positive_factors:
        lines.append("")
        lines.append("✅ Положительные факторы (повышают вероятность одобрения):")
        for f in positive_factors[:5]:
            combo = f.get("combo_label")
            name = f.get("display_name", f.get("feature", ""))
            sp = round(f.get("score_points", 0))
            if combo:
                lines.append(f"  • {combo} → +{abs(sp)} б.")
            else:
                lines.append(f"  • {name}: +{abs(sp)} балла к оценке")

    # 3. Отрицательные факторы
    risk_factors = shap_data.get("risk_factors", [])
    if not risk_factors:
        all_factors = shap_data.get("top_factors", [])
        risk_factors = [f for f in all_factors if f.get("direction") == "negative"]

    if risk_factors:
        lines.append("")
        lines.append("⚠️ Факторы риска (снижают вероятность одобрения):")
        for f in risk_factors[:5]:
            combo = f.get("combo_label")
            name = f.get("display_name", f.get("feature", ""))
            sp = round(abs(f.get("score_points", 0)))
            if combo:
                lines.append(f"  • {combo} → −{sp} б.")
            else:
                severity = "сильное" if sp > 5 else "умеренное" if sp > 1 else "незначительное"
                lines.append(f"  • {name}: −{sp} балла ({severity} влияние)")

    # 4. Сравнение с аналогами
    if peers:
        lines.append("")
        lines.append("📊 Сравнение с аналогами:")

        percentile = peers.get("percentile", 0)
        total = peers.get("total_applications", 0)
        lines.append(f"  • Перцентиль: {percentile}% — заявка выше {percentile}% всех заявок (из {total})")

        region_stats = peers.get("region_stats")
        if region_stats and region_stats.get("cnt", 0) > 0:
            diff = score - region_stats["mean_score"]
            word = "выше" if diff > 0 else "ниже" if diff < 0 else "на уровне"
            lines.append(
                f"  • По региону «{region}»: средний балл {region_stats['mean_score']}, "
                f"эта заявка на {abs(diff):.1f} п. {word} среднего "
                f"(из {region_stats['cnt']} аналогов)"
            )

        direction_stats = peers.get("direction_stats")
        if direction_stats and direction_stats.get("cnt", 0) > 0:
            diff = score - direction_stats["mean_score"]
            word = "выше" if diff > 0 else "ниже" if diff < 0 else "на уровне"
            lines.append(
                f"  • По направлению «{direction}»: средний балл {direction_stats['mean_score']}, "
                f"эта заявка на {abs(diff):.1f} п. {word} среднего "
                f"(из {direction_stats['cnt']} аналогов)"
            )

        subsidy_stats = peers.get("subsidy_stats")
        if subsidy_stats and subsidy_stats.get("cnt", 0) > 0:
            diff = score - subsidy_stats["mean_score"]
            word = "выше" if diff > 0 else "ниже" if diff < 0 else "на уровне"
            lines.append(
                f"  • По виду субсидии «{subsidy_type}»: средний балл {subsidy_stats['mean_score']}, "
                f"эта заявка на {abs(diff):.1f} п. {word} среднего "
                f"(из {subsidy_stats['cnt']} аналогов)"
            )

        global_stats = peers.get("global_stats")
        if global_stats and global_stats.get("cnt", 0) > 0:
            diff = score - global_stats["mean_score"]
            word = "выше" if diff > 0 else "ниже" if diff < 0 else "на уровне"
            lines.append(
                f"  • Глобально: средний балл всех заявок {global_stats['mean_score']}, "
                f"эта заявка на {abs(diff):.1f} п. {word}"
            )

    # 5. Финансовая информация
    if amount or normative:
        lines.append("")
        lines.append("💰 Финансовая информация:")
        if normative:
            lines.append(f"  • Норматив: ₸{normative:,.2f}")
        if amount:
            lines.append(f"  • Причитающаяся сумма: ₸{amount:,.2f}")
        if normative and amount and normative > 0:
            ratio = amount / normative
            lines.append(f"  • Соотношение сумма/норматив: {ratio:.2f}")

    # 6. Рекомендация
    lines.append("")
    if score >= 70:
        lines.append("📋 Рекомендация: Заявка соответствует критериям для одобрения. Финальное решение за комиссией.")
    elif score >= 40:
        lines.append("📋 Рекомендация: Рекомендуется детальное рассмотрение комиссией. Есть как положительные, так и отрицательные факторы.")
    else:
        lines.append("📋 Рекомендация: Заявка имеет высокие риски. Рекомендуется тщательная проверка перед принятием решения.")

    return "\n".join(lines)


@router.get("/applications/{app_id}/analysis")
def get_application_analysis(app_id: int):
    """
    Расширенный анализ заявки:
    - Сравнение с аналогами (по виду субсидии, району, все заявки)
    - Перцентиль (позиция среди всех заявок)
    - Развёрнутое текстовое описание решения
    """
    repo = _repo()

    app = repo.get_by_id(app_id)
    if not app:
        raise HTTPException(404, f"Заявка {app_id} не найдена")

    # Peer comparison
    peers = repo.get_peers(app_id, limit=10)

    # Развёрнутое текстовое описание
    shap_data = app.get("shap_explanation", {})
    narrative = _build_narrative(app, shap_data if isinstance(shap_data, dict) else {}, peers)

    return {
        "app_id": app_id,
        "score": app.get("score", 0),
        "category": app.get("category", ""),
        "narrative": narrative,
        "peers": peers,
    }


# =====================================================================
# SHAP эндпоинт — калиброванные баллы + топ-5 факторов
# =====================================================================

@router.get("/applications/{app_id}/shap")
def get_application_shap(
    app_id: int,
    detailed: bool = Query(False, description="Показать все факторы в rest.factors"),
):
    """
    SHAP-объяснение AI-оценки.

    Логика:
      1. Из БД достаются SHAP-значения (shap_results).
      2. Убираются факторы с нулевым вкладом (округл. до целых).
      3. Сортировка по |SHAP| убыванию.
      4. Топ-5 отдельно, остальные — rest (count + sum).
      5. Если detailed=true → rest.factors со всеми остальными.
      6. Формула: base_value + Σ(all shap) = score.
      7. summary — текст.
      8. fits_budget — укладывается ли в бюджет раунда.
    """
    repo = _repo()
    app = repo.get_by_id(app_id)
    if not app:
        raise HTTPException(404, f"Заявка {app_id} не найдена")

    shap_data = _shap_repo().get_by_application(app_id)

    # Если нет в shap_results — пробуем legacy из applications.shap_explanation
    if not shap_data:
        shap_data = _build_shap_from_legacy(app)
    if not shap_data:
        raise HTTPException(404, f"SHAP-данные для заявки {app_id} не найдены")

    score = shap_data.get("score", round(app.get("score", 0)))
    base_value = 50  # Всегда 50
    model_version = shap_data.get("model_version", app.get("model_version", ""))
    raw_factors = shap_data.get("shap_values", [])

    # Округление и фильтрация
    processed = []
    for f in raw_factors:
        sv = f.get("shap_value", 0)
        rounded_sv = round(sv)
        if rounded_sv == 0:
            continue
        feature_name = f.get("feature", "")
        display = f.get("display_name") or FEATURE_DISPLAY_NAMES.get(feature_name, feature_name)
        processed.append({
            "feature": display,
            "_raw_feature": feature_name,
            "shap_points": rounded_sv,
            "direction": "повышает" if rounded_sv > 0 else "снижает",
            "_raw_shap": sv,
        })

    # Объединение amount + log_amount в один фактор «Причитающая сумма»
    merge_target = MERGE_FEATURES  # {'amount': 'Причитающая сумма', 'log_amount': 'Причитающая сумма'}
    merged: dict[str, dict] = {}
    non_merged = []
    for f in processed:
        raw_feat = f.get("_raw_feature", "")
        if raw_feat in merge_target:
            key = merge_target[raw_feat]
            if key not in merged:
                merged[key] = {"feature": key, "shap_points": 0, "_raw_shap": 0.0}
            merged[key]["shap_points"] += f["shap_points"]
            merged[key]["_raw_shap"] += f["_raw_shap"]
        else:
            non_merged.append(f)

    # Добавляем объединённые факторы
    for key, mf in merged.items():
        if mf["shap_points"] == 0:
            continue
        mf["direction"] = "повышает" if mf["shap_points"] > 0 else "снижает"
        non_merged.append(mf)

    processed = non_merged

    # Сортировка по |shap_points| desc
    processed.sort(key=lambda x: abs(x["shap_points"]), reverse=True)

    # Итоговый балл = 50 + Σ(rounded SHAP) — гарантирует сходимость формулы
    total_shap_sum = sum(f["shap_points"] for f in processed)
    s = max(0, min(100, 50 + total_shap_sum))

    # Топ-5
    top5 = processed[:5]
    rest_items = processed[5:]

    # Формируем factors (без _raw_shap, _raw_feature)
    factors = [
        {"feature": f["feature"], "shap_points": f["shap_points"], "direction": f["direction"]}
        for f in top5
    ]

    # Rest
    rest_sum = sum(f["shap_points"] for f in rest_items)
    rest = {
        "count": len(rest_items),
        "shap_points": rest_sum,
    }
    if detailed and rest_items:
        rest["factors"] = [
            {"feature": f["feature"], "shap_points": f["shap_points"], "direction": f["direction"]}
            for f in rest_items
        ]

    # Динамическая категория из БД
    threshold_repo = _threshold_repo()
    cat_key = threshold_repo.categorize(s, model_version)
    category = CATEGORY_DISPLAY.get(cat_key, cat_key)

    # fits_budget — на основе сохранённого бюджета раунда
    fits_budget = None
    budget_data = threshold_repo.get_round_budget()
    round_budget = budget_data.get("budget", 0)
    if round_budget and round_budget > 0:
        fits_budget = repo.get_fits_budget(app_id, round_budget)

    # Summary
    diff = s - base_value
    if abs(diff) < 5:
        summary = "Ваш балл близок к типичному"
    elif diff > 0:
        summary = f"Ваш балл выше типичного на {abs(diff)} б."
    else:
        summary = f"Ваш балл ниже типичного на {abs(diff)} б."

    return {
        "score": s,
        "base_value": base_value,
        "category": category,
        "model_version": model_version,
        "fits_budget": fits_budget,
        "summary": summary,
        "factors": factors,
        "rest": rest,
    }


def _build_shap_from_legacy(app: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Строит shap_data из legacy shap_explanation (обратная совместимость)."""
    shap_exp = app.get("shap_explanation")
    if not isinstance(shap_exp, dict):
        return None

    all_factors = shap_exp.get("all_factors", [])
    if not all_factors:
        all_factors = shap_exp.get("top_factors", [])
    if not all_factors:
        return None

    factors = []
    for f in all_factors:
        sv = f.get("score_points", f.get("shap_value", 0))
        factors.append({
            "feature": f.get("feature", ""),
            "display_name": f.get("display_name", f.get("feature", "")),
            "shap_value": sv,
            "feature_value": f.get("value", 0),
        })

    return {
        "score": round(app.get("score", 0)),
        "base_value": round(shap_exp.get("base_score", shap_exp.get("base_value", 50))),
        "model_version": app.get("model_version", ""),
        "shap_values": factors,
    }
