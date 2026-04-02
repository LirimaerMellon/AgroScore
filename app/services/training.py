"""
TrainingService — оркестрация полного пайплайна обучения.

Поток:
  DataFrame → Mapper → Cleaner → TargetVariable → FeatureEngineer(fit_transform)
  → ScoringModel(train) → save model + FE → ModelRepository
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

import numpy as np
import pandas as pd

from app.config import MODELS_DIR


def _to_native(obj):
    """Рекурсивно конвертирует numpy типы в Python native для JSON."""
    if isinstance(obj, dict):
        return {k: _to_native(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_native(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        v = float(obj)
        return None if np.isnan(v) or np.isinf(v) else v
    if isinstance(obj, float):
        return None if np.isnan(obj) or np.isinf(obj) else obj
    if isinstance(obj, np.ndarray):
        return _to_native(obj.tolist())
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    return obj


from app.database.repository import ErrorLogRepository
from app.database.model_repository import ModelRepository
from app.pipeline.mapper import ColumnMapper
from app.pipeline.cleaner import DataCleaner
from app.pipeline.features import FeatureEngineer
from app.pipeline.model import ScoringModel

logger = logging.getLogger(__name__)


class TrainingService:

    def __init__(
        self,
        error_repo: ErrorLogRepository,
        model_repo: ModelRepository,
    ):
        self.error_repo = error_repo
        self.model_repo = model_repo

    def train(
        self,
        df: pd.DataFrame,
        source_name: str,
        source_type: str = "excel",
        model_version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Полный цикл обучения.

        Параметры:
          df            — сырые данные (русские или English колонки)
          source_name   — имя файла (для error_logs)
          source_type   — 'excel' | 'csv' | 'json'
          model_version — если указан, дообучение существующей модели

        Возвращает словарь с метриками, версией, fairness и т.д.
        """
        # 1. Маппинг колонок
        mapper = ColumnMapper()
        df = mapper.map_training(df)
        mapper.validate_training(df)

        total_raw = len(df)

        # 2. Очистка
        cleaner = DataCleaner(error_repo=self.error_repo)
        df = cleaner.clean_data(df, source_name=source_name, source_type=source_type, mode="training")
        df = cleaner.add_target_variable(df, source_name=source_name, source_type=source_type)
        trace_id = cleaner.last_trace_id

        if len(df) < 10:
            raise ValueError(
                f"Слишком мало данных после очистки: {len(df)} строк. "
                f"Минимум 10 для обучения."
            )

        # 3. Feature engineering (fit + transform)
        fe = FeatureEngineer()
        enriched = fe.fit_transform(df)

        # 4. Обучение модели
        model = ScoringModel()
        base_model = None

        if model_version:
            model_info = self.model_repo.get_by_version(model_version)
            if model_info:
                old_model = ScoringModel()
                old_model.load(model_info['file_path'])
                base_model = old_model.model
                logger.info(f"Fine-tuning от модели: {model_version}")

        metrics = model.train(enriched, base_model=base_model)

        # 5. Скоринг обучающих данных (для fairness)
        scored = model.score(enriched)
        fairness = model.compute_fairness_report(scored)

        # 6. Feature importance
        fi = model.get_feature_importance()

        # 7. Сохранение модели на диск
        version = model_version or f"v_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        model_path = MODELS_DIR / f"{version}.pkl"
        model.save(str(model_path), feature_engineer=fe)

        # 8. Регистрация в БД
        self.model_repo.create(
            version=version,
            file_path=str(model_path),
            metrics=metrics,
            train_size=metrics['train_size'],
            n_features=metrics['n_features'],
            positive_rate=metrics['positive_rate'],
        )

        logger.info(f"Обучение завершено: версия={version}")

        return _to_native({
            "status": "success",
            "model_version": version,
            "total_raw_records": total_raw,
            "cleaned_records": len(df),
            "metrics": metrics,
            "fairness": fairness,
            "feature_importance": fi.head(15).to_dict("records"),
            "trace_id": trace_id,
        })

