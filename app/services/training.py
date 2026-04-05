"""
TrainingService — оркестрация полного пайплайна обучения.

Поток:
  DataFrame -> Mapper -> Cleaner -> TargetVariable -> FeatureEngineer(fit_transform)
  -> ScoringModel(train) -> save model + FE -> ModelRepository
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any

import numpy as np
import pandas as pd

from app.config import MODELS_DIR

from app.database.repository import ErrorLogRepository
from app.database.model_repository import ModelRepository
from app.pipeline.mapper import ColumnMapper
from app.pipeline.cleaner import DataCleaner
from app.pipeline.features import FeatureEngineer
from app.pipeline.model import ScoringModel

logger = logging.getLogger(__name__)


def _to_native(obj):
    """Рекурсивно конвертирует numpy-типы в стандартные Python-типы для JSON-сериализации."""
    if isinstance(obj, dict):
        return {k: _to_native(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_native(v) for v in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        v = float(obj)
        return None if np.isnan(v) or np.isinf(v) else v
    if isinstance(obj, float):
        return None if np.isnan(obj) or np.isinf(obj) else obj
    if isinstance(obj, np.ndarray):
        return _to_native(obj.tolist())
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj




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
    ) -> Dict[str, Any]:
        """
        Полный цикл обучения с нуля.

        Параметры:
          df            — сырые данные (русские или English колонки)
          source_name   — имя файла (для error_logs)
          source_type   — 'excel' | 'csv' | 'json'

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

        metrics = model.train(enriched)

        # 5. Скоринг обучающих данных (для fairness)
        scored = model.score(enriched)
        # model.score() возвращает score=None (AI-балл считается только в ScoringService).
        # Для fairness-анализа при обучении используем probability × 100 как прокси.
        scored['score'] = np.clip(np.round(scored['probability'] * 100, 2), 0, 100)
        fairness = model.compute_fairness_report(scored)

        # 6. Feature importance
        fi = model.get_feature_importance()

        # 7. Сохранение модели на диск
        version = f"v_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        version_dir = MODELS_DIR / version
        version_dir.mkdir(parents=True, exist_ok=True)
        model_path = version_dir / "model.pkl"
        model.save(str(model_path), feature_engineer=fe)

        # 7.1 Сохранение отдельных артефактов для деплоя
        model.save_artifacts(str(version_dir))

        # 7.2 Сохранение маппинга известных категориальных значений
        known_cats = {
            col: sorted(list(vals))
            for col, vals in fe._known_categories.items()
        }
        with open(version_dir / "known_categories.json", "w", encoding="utf-8") as f:
            json.dump(known_cats, f, ensure_ascii=False, indent=2)
        logger.info(f"Known categories сохранены: {version_dir / 'known_categories.json'}")

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

