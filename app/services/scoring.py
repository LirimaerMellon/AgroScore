"""
ScoringService — оркестрация inference-пайплайна.

Поток:
  DataFrame -> Mapper -> Cleaner(inference) -> FeatureEngineer(transform)
  -> ScoringModel(score) -> SHAP(CalibratedExplainer) -> DB

AI-балл считается строго из SHAP-значений: clip(round(50 + sum(SHAP)), 0, 100).
"""

import logging
from typing import Dict, Any, Optional, List

import pandas as pd

from app.database.repository import ErrorLogRepository
from app.database.model_repository import ModelRepository
from app.database.app_repository import ApplicationRepository
from app.database.shap_repository import ShapRepository
from app.database.threshold_repository import ThresholdRepository
from app.pipeline.mapper import ColumnMapper
from app.pipeline.cleaner import DataCleaner
from app.pipeline.features import FeatureEngineer
from app.pipeline.model import ScoringModel
from app.pipeline.explainer import CalibratedExplainer, _extract_shap_values, _safe_float, _distribute_delta

logger = logging.getLogger(__name__)

# Маппинг internal → русское название для предупреждений
_FIELD_DISPLAY = {
    'direction': 'Направление',
    'subsidy_type': 'Вид субсидии',
    'district': 'Район',
}


def _category_from_score(score: int) -> str:
    """Определяет категорию строго по AI-баллу.

    70–100 → HIGH, 40–69 → MEDIUM, 0–39 → LOW.
    """
    if score >= 70:
        return "HIGH"
    if score >= 40:
        return "MEDIUM"
    return "LOW"


class ScoringService:

    def __init__(
        self,
        error_repo: ErrorLogRepository,
        model_repo: ModelRepository,
        app_repo: ApplicationRepository,
        shap_repo: Optional[ShapRepository] = None,
        threshold_repo: Optional[ThresholdRepository] = None,
    ):
        self.error_repo = error_repo
        self.model_repo = model_repo
        self.app_repo = app_repo
        self.shap_repo = shap_repo
        self.threshold_repo = threshold_repo

    def score(
        self,
        df: pd.DataFrame,
        source_name: str,
        source_type: str = "excel",
        model_version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Скоринг новых заявок с калиброванными баллами (0–100) и SHAP.
        """
        # 1. Загрузка модели
        model_info = None
        if model_version:
            model_info = self.model_repo.get_by_version(model_version)
        if not model_info:
            model_info = self.model_repo.get_active()
        if not model_info:
            raise ValueError("Нет обученной модели. Сначала обучите модель, загрузив исторические данные на странице «Модели».")

        model = ScoringModel()
        fe: FeatureEngineer = model.load(model_info['file_path'])

        if fe is None or not fe._fitted:
            raise ValueError("Модель не содержит данные FeatureEngineer. Переобучите модель.")

        # Обратная совместимость
        if not getattr(fe, '_known_categories', None):
            logger.warning("FE не содержит _known_categories — реконструкция из label_encoders модели")
            fe._known_categories = {}
            for col, le in model.label_encoders.items():
                fe._known_categories[col] = set(le.classes_)

        # 2. Маппинг колонок
        mapper = ColumnMapper()
        df = mapper.map_inference(df)
        mapper.validate_inference(df)

        total_raw = len(df)

        # 3. Очистка
        cleaner = DataCleaner(error_repo=self.error_repo)
        df_clean = cleaner.clean_data(
            df, source_name=source_name, source_type=source_type, mode="inference"
        )
        trace_id = cleaner.last_trace_id

        if df_clean.empty:
            raise ValueError("После очистки не осталось валидных строк.")

        bin_iin_series = df_clean['bin_iin'].copy() if 'bin_iin' in df_clean.columns else None

        # 3.5 Неизвестные поля
        unknown_fields_per_row = fe.get_unknown_fields(df_clean)

        # 4. Feature engineering
        enriched = fe.transform(df_clean, is_training=False)

        # 5. Метаданные скоринга (probability, confidence и т.д.)
        # ⚠ model.score() НЕ вычисляет AI-балл (score=None, category=None).
        # AI-балл считается ниже из SHAP-значений.
        scored = model.score(enriched)

        # 5.5 Закодированные фичи для SHAP
        X_encoded = model.prepare_features(enriched.copy(), fit=False)

        # 6. SHAP — CalibratedExplainer или fallback
        has_calibration = (
            model.quantile_transformer is not None
            and model.X_background is not None
        )

        shap_results_list: List[Dict[str, Any]] = []

        if has_calibration:
            try:
                cal_explainer = CalibratedExplainer(
                    raw_model=model.model,
                    calibrated_fn=model.calibrated_predict,
                    background=model.X_background,
                    feature_names=model.feature_names,
                )
                shap_results_list = cal_explainer.explain_batch(
                    X_encoded,
                    original_df=df_clean,
                )
            except Exception as e:
                logger.warning(f"CalibratedExplainer failed: {e}, falling back")
                has_calibration = False

        if not has_calibration:
            # Fallback — TreeExplainer батчем (без калибровки)
            try:
                import shap as _shap
                import numpy as _np
                tree_exp = _shap.TreeExplainer(model.model)
                raw_shap = tree_exp.shap_values(X_encoded)
                shap_vals = _extract_shap_values(raw_shap)
                if isinstance(shap_vals, list):
                    shap_vals = _np.array(shap_vals)
                probabilities = model.model.predict_proba(X_encoded)[:, 1]

                from app.config import FEATURE_DISPLAY_NAMES as _FDN

                for i in range(len(X_encoded)):
                    prob = float(probabilities[i])
                    score = max(0, min(100, round(prob * 100)))
                    delta = score - 50

                    sv_raw = [_safe_float(v) for v in shap_vals[i]]
                    int_contribs = _distribute_delta(delta, sv_raw)

                    factors = []
                    for j, fname in enumerate(model.feature_names):
                        factors.append({
                            "feature": fname,
                            "display_name": _FDN.get(fname, fname),
                            "shap_value": int_contribs[j],
                            "feature_value": _safe_float(X_encoded.iloc[i][fname]) if fname in X_encoded.columns else 0,
                        })
                    shap_results_list.append({
                        "base_value": 50,
                        "score": score,
                        "factors": factors,
                    })
            except Exception as e:
                logger.warning(f"FeatureExplainer fallback failed: {e}")
                for _ in range(len(X_encoded)):
                    shap_results_list.append({
                        "base_value": 50,
                        "score": 50,
                        "factors": [],
                    })

        # 7. Формирование записей
        applications: List[Dict[str, Any]] = []
        scored_indices = scored.index.tolist()

        for i, idx in enumerate(scored_indices):
            row = scored.loc[idx]

            unknowns = unknown_fields_per_row[i] if i < len(unknown_fields_per_row) else []
            unknown_count = len(unknowns)

            # Уровень доверия к AI-оценке
            if unknown_count == 0:
                confidence_level = "HIGH"
            elif unknown_count <= 2:
                confidence_level = "MEDIUM"
            else:
                confidence_level = "LOW"

            warnings = []
            for field in unknowns:
                display = _FIELD_DISPLAY.get(field, field)
                raw_val = str(df_clean.iloc[i].get(field, ""))
                warnings.append({
                    "field": field,
                    "display_name": display,
                    "value": raw_val,
                    "message": f"Значение «{raw_val}» в поле «{display}» не встречалось в обучающих данных",
                })

            confidence = float(row.get("confidence", 1.0))
            review_required = confidence_level in ("MEDIUM", "LOW")
            data_quality = str(row.get("data_quality", "complete"))

            if review_required:
                warnings.append({
                    "field": "_review",
                    "display_name": "Рекомендация",
                    "value": data_quality,
                    "message": (
                        "Часть данных заявки отсутствует в обучающей выборке модели. "
                        "Рекомендуется ручная проверка комиссией. "
                        f"Уровень полноты данных: {data_quality}."
                    ),
                })

            # ---- AI-балл строго из SHAP-значений (целочисленных) ----
            shap_data = shap_results_list[i] if i < len(shap_results_list) else {}
            factors = shap_data.get("factors", [])
            shap_sum = sum(f.get("shap_value", 0) for f in factors)
            ai_score = max(0, min(100, 50 + shap_sum))
            ai_category = _category_from_score(ai_score)

            # Валидация: 50 + sum(SHAP) == AI-балл (точное равенство)
            if 50 + shap_sum != ai_score:
                logger.error(
                    f"AI-балл не сходится: row={i}, ai_score={ai_score}, "
                    f"50+sum(SHAP)={50 + shap_sum}"
                )

            # Упрощённый shap_explanation для обратной совместимости
            legacy_explanation = self._build_legacy_explanation(shap_data)

            app_data = {
                "model_version": model_info["version"],
                "bin_iin": str(bin_iin_series.iloc[i]) if bin_iin_series is not None else "",
                "region": str(df_clean.iloc[i].get("region", "")) if "region" in df_clean.columns else "",
                "akimat": str(df_clean.iloc[i].get("akimat", "")) if "akimat" in df_clean.columns else "",
                "direction": str(row.get("direction", "")),
                "subsidy_type": str(row.get("subsidy_type", "")),
                "normative": float(row.get("normative", 0)),
                "amount": float(row.get("amount", 0)),
                "district": str(row.get("district", "")),
                "score": float(ai_score),
                "category": ai_category,
                "probability": float(row["probability"]),
                "confidence": confidence,
                "confidence_level": confidence_level,
                "unknown_fields": unknowns,
                "review_required": review_required,
                "data_quality": data_quality,
                "data_warnings": warnings,
                "shap_explanation": legacy_explanation,
            }
            applications.append(app_data)

        # 8. Сохранение заявок в БД
        app_ids = self.app_repo.create_batch(applications)
        for i, app_id in enumerate(app_ids):
            applications[i]["id"] = app_id

        # 9. Сохранение SHAP в shap_results
        if self.shap_repo:
            shap_entries = []
            for i, app_id in enumerate(app_ids):
                if i < len(shap_results_list):
                    shap_data = shap_results_list[i]
                    # AI-балл в shap_results тоже из SHAP (= applications[i]["score"])
                    shap_entries.append({
                        "object_id": app_id,
                        "model_version": model_info["version"],
                        "score": round(float(applications[i]["score"])),
                        "base_value": 50,
                        "shap_values": shap_data.get("factors", []),
                    })
            if shap_entries:
                try:
                    self.shap_repo.save_batch(shap_entries)
                except Exception as e:
                    logger.warning(f"Ошибка сохранения SHAP: {e}")

        # Сортировка
        applications.sort(key=lambda x: x["score"], reverse=True)

        # Подсчёт категорий
        categories = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for a in applications:
            cat = a["category"]
            if cat in categories:
                categories[cat] += 1

        total_with_warnings = sum(1 for a in applications if a.get("data_warnings"))
        total_review = sum(1 for a in applications if a.get("review_required"))
        global_warnings = []
        if total_review > 0:
            global_warnings.append(
                f"{total_review} из {len(applications)} заявок рекомендованы к ручной проверке "
                f"(часть данных не встречалась в обучающей выборке)."
            )
        elif total_with_warnings > 0:
            global_warnings.append(
                f"{total_with_warnings} из {len(applications)} заявок содержат "
                f"значения, неизвестные модели. Уверенность оценки снижена."
            )

        logger.info(
            f"Скоринг завершён: {len(applications)} заявок "
            f"(HIGH={categories['HIGH']}, MEDIUM={categories['MEDIUM']}, LOW={categories['LOW']})"
        )

        return {
            "status": "success",
            "model_version": model_info["version"],
            "total_raw": total_raw,
            "total_scored": len(applications),
            "trace_id": trace_id,
            "categories": categories,
            "warnings": global_warnings,
            "applications": applications,
        }

    @staticmethod
    def _build_legacy_explanation(shap_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создаёт shap_explanation в старом формате для обратной совместимости."""
        factors = shap_data.get("factors", [])

        # AI-балл = 50 + sum(SHAP), base_value всегда 50
        shap_sum = sum(f.get("shap_value", 0) for f in factors)
        score = max(0, min(100, 50 + shap_sum))

        sorted_factors = sorted(factors, key=lambda f: abs(f.get("shap_value", 0)), reverse=True)

        top_factors = []
        all_factors = []
        for f in sorted_factors:
            sv = f.get("shap_value", 0)
            entry = {
                "feature": f.get("feature", ""),
                "display_name": f.get("display_name", f.get("feature", "")),
                "value": f.get("feature_value", 0),
                "shap_value": sv,
                "score_points": sv,
                "direction": "positive" if sv > 0 else "negative",
            }
            all_factors.append(entry)
            if len(top_factors) < 10:
                entry["importance"] = abs(sv)
                top_factors.append(entry)

        return {
            "top_factors": top_factors,
            "risk_factors": [f for f in top_factors if f["direction"] == "negative"],
            "positive_factors": [f for f in top_factors if f["direction"] == "positive"],
            "all_factors": all_factors,
            "base_value": 50,
            "base_score": 50,
            "predicted_score": score,
            "method": "SHAP",
        }
