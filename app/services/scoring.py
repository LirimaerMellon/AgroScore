"""
ScoringService — оркестрация inference-пайплайна.

Поток:
  DataFrame → Mapper → Cleaner(inference) → FeatureEngineer(transform)
  → ScoringModel(score) → confidence adjustment → SHAP explain → ApplicationRepository

Enterprise-подход к качеству данных:
  Неизвестные категориальные значения → мягкий дисконт confidence + прозрачные
  индикаторы data_quality / review_required. Модель не «наказывает» новых
  заявителей, а информирует комиссию об уровне уверенности в оценке.
  Финальное решение остаётся за человеком.
"""

import logging
from typing import Dict, Any, Optional, List

import numpy as np
import pandas as pd

from app.database.repository import ErrorLogRepository
from app.database.model_repository import ModelRepository
from app.database.app_repository import ApplicationRepository
from app.pipeline.mapper import ColumnMapper
from app.pipeline.cleaner import DataCleaner
from app.pipeline.features import FeatureEngineer
from app.pipeline.model import ScoringModel
from app.pipeline.explainer import FeatureExplainer
from app.config import FEATURE_DISPLAY_NAMES

logger = logging.getLogger(__name__)

# Маппинг internal → русское название для предупреждений
_FIELD_DISPLAY = {
    'region': 'Область',
    'akimat': 'Акимат',
    'direction': 'Направление',
    'subsidy_type': 'Вид субсидии',
    'district': 'Район',
}


class ScoringService:

    def __init__(
        self,
        error_repo: ErrorLogRepository,
        model_repo: ModelRepository,
        app_repo: ApplicationRepository,
    ):
        self.error_repo = error_repo
        self.model_repo = model_repo
        self.app_repo = app_repo

    def score(
        self,
        df: pd.DataFrame,
        source_name: str,
        source_type: str = "excel",
        model_version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Скоринг новых заявок.

        Параметры:
          df             — данные заявок (inference-шаблон)
          source_name    — имя файла
          model_version  — конкретная версия модели (или активная)

        Возвращает список оценённых заявок с SHAP-объяснениями и предупреждениями.
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

        # Обратная совместимость: если FE из старого pickle не имеет
        # _known_categories, реконструируем из label_encoders модели.
        if not getattr(fe, '_known_categories', None):
            logger.warning("FE не содержит _known_categories — реконструкция из label_encoders модели")
            fe._known_categories = {}
            for col, le in model.label_encoders.items():
                fe._known_categories[col] = set(le.classes_)

        # Обратная совместимость: если FE не имеет _fill_q25
        if not getattr(fe, '_fill_q25', None):
            fe._fill_q25 = {}

        # 2. Маппинг колонок
        mapper = ColumnMapper()
        df = mapper.map_inference(df)
        mapper.validate_inference(df)

        total_raw = len(df)

        # 3. Очистка (inference mode — без дат, статусов, номера заявки)
        cleaner = DataCleaner(error_repo=self.error_repo)
        df_clean = cleaner.clean_data(
            df, source_name=source_name, source_type=source_type, mode="inference"
        )
        trace_id = cleaner.last_trace_id

        if df_clean.empty:
            raise ValueError("После очистки не осталось валидных строк.")

        # Сохраняем bin_iin до feature engineering (он исключается из фичей)
        bin_iin_series = df_clean['bin_iin'].copy() if 'bin_iin' in df_clean.columns else None

        # 3.5 Определяем неизвестные поля для каждой строки ДО трансформации
        unknown_fields_per_row = fe.get_unknown_fields(df_clean)

        # 4. Feature engineering (transform — используем сохранённые статистики)
        enriched = fe.transform(df_clean, is_training=False)

        # 5. Скоринг (с учётом confidence penalty)
        scored = model.score(enriched)

        # 5.5 Подготовить закодированные фичи для SHAP (label-encoded)
        X_encoded = model.prepare_features(enriched.copy(), fit=False)

        # 6. SHAP-объяснения
        explainer = FeatureExplainer(
            model.model,
            model.feature_names,
            X_encoded,
        )

        applications: List[Dict[str, Any]] = []
        scored_indices = scored.index.tolist()

        for i, idx in enumerate(scored_indices):
            row = scored.loc[idx]
            X_single = X_encoded.loc[[idx]]

            try:
                explanation = explainer.explain_single(X_single)
            except Exception as e:
                logger.warning(f"SHAP error для строки {idx}: {e}")
                explanation = {"top_factors": [], "all_factors": [], "method": "SHAP"}

            # Предупреждения о неизвестных полях
            unknowns = unknown_fields_per_row[i] if i < len(unknown_fields_per_row) else []
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
            review_required = bool(row.get("review_required", False))
            data_quality = str(row.get("data_quality", "complete"))

            # Enterprise-предупреждение: информативное, не карательное
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

            app_data = {
                "model_version": model_info["version"],
                "bin_iin": str(bin_iin_series.iloc[i]) if bin_iin_series is not None else "",
                "region": str(row.get("region", "")),
                "akimat": str(row.get("akimat", "")),
                "direction": str(row.get("direction", "")),
                "subsidy_type": str(row.get("subsidy_type", "")),
                "normative": float(row.get("normative", 0)),
                "amount": float(row.get("amount", 0)),
                "district": str(row.get("district", "")),
                "score": float(row["score"]),
                "category": str(row["category"]),
                "probability": float(row["probability"]),
                "confidence": confidence,
                "review_required": review_required,
                "data_quality": data_quality,
                "data_warnings": warnings,
                "shap_explanation": explanation,
            }
            applications.append(app_data)

        # 7. Сохранение в БД
        app_ids = self.app_repo.create_batch(applications)
        for i, app_id in enumerate(app_ids):
            applications[i]["id"] = app_id

        # Сортировка по скору (лучшие сверху)
        applications.sort(key=lambda x: x["score"], reverse=True)

        # Подсчёт категорий
        categories = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for a in applications:
            cat = a["category"]
            if cat in categories:
                categories[cat] += 1

        # Общие предупреждения
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
            f"{f' | {total_with_warnings} с предупреждениями' if total_with_warnings else ''}"
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

