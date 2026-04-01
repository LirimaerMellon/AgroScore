import argparse
import logging
from datetime import datetime
from pathlib import Path

from app.pipeline.loader import DataLoader
from app.pipeline.cleaner import DataCleaner
from app.pipeline.features import FeatureEngineer
from app.pipeline.model import ScoringModel
from app.database import Database, ErrorLogRepository
from app.config import MODELS_DIR, DB_PATH, COLUMN_RENAME_MAP

DEBUG_DIR = Path("data/debug")
RESULTS_DIR = Path("data/results")

DEBUG_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main(input_file, output_file, model_file):
    try:
        logger.info("=" * 60)
        logger.info("СИСТЕМА ОЦЕНКИ СУБСИДИЙ — ОБУЧЕНИЕ")
        logger.info("=" * 60)

        input_path = Path(input_file)
        if not input_path.exists():
            logger.error(f"Файл не найден: {input_file}")
            return

        logger.info(f"Входной файл: {input_file}")

        # --- Инициализация БД для логирования ошибок ---
        db = Database(str(DB_PATH))
        db.init_schema()
        error_repo = ErrorLogRepository(db)
        logger.info(f"SQLite подключена: {DB_PATH}")

        # --- Загрузка ---
        loader = DataLoader()
        raw_data = loader.load_data(input_file)

        # Переименование колонок (если excel с русскими названиями)
        raw_data = raw_data.rename(columns=COLUMN_RENAME_MAP)

        logger.info(f"Строк: {len(raw_data)}")
        raw_data.to_csv(DEBUG_DIR / "raw_data.csv", index=False)

        loader.validate_columns(raw_data)

        # --- Очистка с логированием ошибок в БД ---
        source_name = input_path.name
        source_type = "csv" if source_name.endswith(".csv") else "excel"

        cleaner = DataCleaner(error_repo=error_repo)
        cleaned_data = cleaner.clean_data(
            raw_data,
            source_name=source_name,
            source_type=source_type,
        )

        logger.info(f"Строк после очистки: {len(cleaned_data)}")
        cleaned_data.to_csv(DEBUG_DIR / "cleaned_data.csv", index=False)

        cleaned_data = cleaner.add_target_variable(
            cleaned_data,
            source_name=source_name,
            source_type=source_type,
        )

        logger.info(f"Строк после таргета: {len(cleaned_data)}")
        cleaned_data.to_csv(DEBUG_DIR / "with_target.csv", index=False)

        # --- Лог ошибок очистки ---
        if cleaner.last_trace_id:
            summary = error_repo.get_summary(cleaner.last_trace_id)
            logger.info(f"Ошибок очистки: {summary['total_errors']} (trace={cleaner.last_trace_id[:8]}…)")

        # --- Feature engineering ---
        logger.info("Feature engineering...")
        fe = FeatureEngineer(cleaned_data)
        fe.calculate_approval_rates()
        fe.calculate_financial_aggregates()
        enriched_data = fe.enrich_dataset()

        logger.info(f"Обогащённых строк: {len(enriched_data)}")
        enriched_data.to_csv(DEBUG_DIR / "enriched_data.csv", index=False)

        # --- Обучение модели (с CV) ---
        model = ScoringModel()
        metrics = model.train(enriched_data)
        logger.info(f"Метрики (CV): {metrics}")

        # --- Feature importance ---
        fi = model.get_feature_importance()
        fi.to_csv(DEBUG_DIR / "feature_importance.csv", index=False)
        logger.info(f"Топ-10 признаков:\n{fi.head(10).to_string(index=False)}")

        # --- Скоринг ---
        logger.info("Скоринг...")
        scored_data = model.score(enriched_data)
        scored_data = scored_data.sort_values('score', ascending=False)

        logger.info(f"Оценённых строк: {len(scored_data)}")
        logger.info(f"  HIGH:   {len(scored_data[scored_data['category'] == 'HIGH'])}")
        logger.info(f"  MEDIUM: {len(scored_data[scored_data['category'] == 'MEDIUM'])}")
        logger.info(f"  LOW:    {len(scored_data[scored_data['category'] == 'LOW'])}")

        # --- Fairness ---
        fairness = model.compute_fairness_report(scored_data)
        for group_key, stats in fairness.items():
            if '_disparate_impact' in group_key:
                logger.info(f"Disparate Impact ({group_key}): {stats}")

        # --- Сохранение результатов ---
        if output_file is None:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = RESULTS_DIR / f"result_{ts}.xlsx"
        else:
            output_file = Path(output_file)

        output_file.parent.mkdir(parents=True, exist_ok=True)
        scored_data.to_excel(output_file, index=False)
        logger.info(f"Результат сохранён: {output_file}")

        # --- Сохранение модели ---
        MODELS_DIR.mkdir(parents=True, exist_ok=True)

        if model_file is None:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            model_file = MODELS_DIR / f"model_{ts}.pkl"
        else:
            model_file = Path(model_file)

        model.save(str(model_file))
        logger.info(f"Модель сохранена: {model_file}")

        logger.info("=" * 60)
        logger.info("ОБУЧЕНИЕ ЗАВЕРШЕНО УСПЕШНО")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Тренировка модели AgriScore")

    parser.add_argument("--input", required=True, help="Входящий файл (.csv or .xlsx)")
    parser.add_argument("--output", default=None, help="Выходящий Excel file")
    parser.add_argument("--model", default=None, help="Выходящая модель (.pkl)")

    args = parser.parse_args()
    main(args.input, args.output, args.model)