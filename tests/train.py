"""
CLI-обёртка для обучения модели AgriScore.

Использование:
    python tests/train.py --input data/raw/file.xlsx
    python tests/train.py --input data/raw/file.xlsx --model-version v_custom
"""

import argparse
import logging
import sys
import os
from pathlib import Path

# Корень проекта в sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from app.pipeline.loader import DataLoader
from app.database import Database, ErrorLogRepository, ModelRepository
from app.services.training import TrainingService
from app.config import DB_PATH

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


def main(input_file: str, model_version: str = None):
    try:
        logger.info("=" * 60)
        logger.info("AGRISCORE — ОБУЧЕНИЕ МОДЕЛИ (CLI)")
        logger.info("=" * 60)

        input_path = Path(input_file)
        if not input_path.exists():
            logger.error(f"Файл не найден: {input_file}")
            return

        # Инициализация БД
        db = Database(str(DB_PATH))
        db.init_schema()

        # Загрузка данных
        loader = DataLoader(required_columns=[])
        df = loader.load_data(str(input_path))

        source_type = "csv" if input_path.suffix == ".csv" else "excel"

        # Обучение через сервис
        service = TrainingService(
            error_repo=ErrorLogRepository(db),
            model_repo=ModelRepository(db),
        )

        result = service.train(
            df=df,
            source_name=input_path.name,
            source_type=source_type,
            model_version=model_version,
        )

        # Вывод результатов
        logger.info("=" * 60)
        logger.info(f"Модель: {result['model_version']}")
        logger.info(f"Записей (сырых): {result['total_raw_records']}")
        logger.info(f"Записей (чистых): {result['cleaned_records']}")
        logger.info(f"AUC: {result['metrics'].get('auc_mean', 'N/A')}")
        logger.info(f"F1:  {result['metrics'].get('f1_mean', 'N/A')}")
        logger.info(f"Trace ID: {result['trace_id']}")
        logger.info("=" * 60)
        logger.info("ОБУЧЕНИЕ ЗАВЕРШЕНО УСПЕШНО")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Обучение модели AgriScore")
    parser.add_argument("--input", required=True, help="Входной файл (.xlsx/.csv)")
    parser.add_argument("--model-version", default=None, help="Версия модели (для дообучения)")

    args = parser.parse_args()
    main(args.input, args.model_version)

