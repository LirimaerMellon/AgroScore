import argparse
import logging
from datetime import datetime
from pathlib import Path

from app.pipeline.loader import load_data, validate_columns
from app.pipeline.cleaner import clean_data, add_target_variable
from app.pipeline.features import FeatureEngineer
from app.pipeline.model import ScoringModel
from app.config import MODELS_DIR

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
        logger.info("СИСТЕМА ОЦЕНКИ СУБСИДИЙ - ОБУЧЕНИЕ")
        logger.info("=" * 60)

        input_path = Path(input_file)

        if not input_path.exists():
            logger.error(f"Файл не найден: {input_file}")
            return

        logger.info(f"Входной файл: {input_file}")

        raw_data = load_data(input_file)
        logger.info(f"Строк: {len(raw_data)}")

        raw_data.to_csv(DEBUG_DIR / "raw_data.csv", index=False)

        is_valid, missing = validate_columns(raw_data)
        if not is_valid:
            raise ValueError(f"Не найдены столбцы: {missing}")

        logger.info("Фильтруем данные...")
        cleaned_data = clean_data(raw_data)

        logger.info(f"Строк: {len(cleaned_data)}")
        cleaned_data.to_csv(DEBUG_DIR / "cleaned_data.csv", index=False)

        cleaned_data = add_target_variable(cleaned_data)

        logger.info(f"После таргета: {len(cleaned_data)}")
        cleaned_data.to_csv(DEBUG_DIR / "with_target.csv", index=False)

        logger.info("В процессе...")
        fe = FeatureEngineer(cleaned_data)

        fe.calculate_approval_rates()
        fe.calculate_financial_aggregates()

        enriched_data = fe.enrich_dataset()

        logger.info(f"Загруженные строки: {len(enriched_data)}")
        enriched_data.to_csv(DEBUG_DIR / "enriched_data.csv", index=False)

        logger.info("Тренируем модель...")
        model = ScoringModel()
        metrics = model.train(enriched_data)

        logger.info(f"Метрики: {metrics}")

        logger.info("Подсчет...")
        scored_data = model.score(enriched_data)
        scored_data = scored_data.sort_values('score', ascending=False)

        logger.info(f"Оцененных строк: {len(scored_data)}")
        logger.info(f"Высоко оцененные: {len(scored_data[scored_data['category'] == 'HIGH'])}")
        logger.info(f"Средне оцененные: {len(scored_data[scored_data['category'] == 'MEDIUM'])}")
        logger.info(f"Низко оцененные: {len(scored_data[scored_data['category'] == 'LOW'])}")

        if output_file is None:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = RESULTS_DIR / f"result_{ts}.xlsx"
        else:
            output_file = Path(output_file)

        output_file.parent.mkdir(parents=True, exist_ok=True)

        scored_data.to_excel(output_file, index=False)

        logger.info(f"Результат сохранен: {output_file}")

        MODELS_DIR.mkdir(parents=True, exist_ok=True)

        if model_file is None:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            model_file = MODELS_DIR / f"model_{ts}.pkl"
        else:
            model_file = Path(model_file)

        model.save(str(model_file))

        logger.info(f"Модель сохранена: {model_file}")

        logger.info("=" * 60)
        logger.info("Тренировка модели прошла успешно")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Тренировка модели")

    parser.add_argument("--input", required=True, help="Входящий файл (.csv or .xlsx)")
    parser.add_argument("--output", default=None, help="Выходящий Excel file")
    parser.add_argument("--model", default=None, help="Выходящая модель")

    args = parser.parse_args()

    main(args.input, args.output, args.model)