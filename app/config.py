"""
Единая конфигурация проекта AgriScore.

Содержит пути к данным, маппинг колонок, бизнес-правила,
параметры модели и настройки API.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"

RAW_DATA_DIR = DATA_DIR / "raw"
MODELS_DIR = DATA_DIR / "models"
DEBUG_DIR = DATA_DIR / "debug"
RESULTS_DIR = DATA_DIR / "results"
FEATURES_DIR = DATA_DIR / "features"

DB_PATH = DATA_DIR / "agriscore.db"

COLUMN_RENAME_MAP = {
    '№ п/п': 'row_number',
    'Дата поступления': 'submission_date',
    'Область': 'region',
    'Акимат': 'akimat',
    'Номер заявки': 'request_number',
    'Направление водства': 'direction',
    'Наименование субсидирования': 'subsidy_type',
    'Статус заявки': 'status',
    'Норматив': 'normative',
    'Причитающая сумма': 'amount',
    'Район хозяйства': 'district',
}

INFERENCE_RENAME_MAP = {
    'Область': 'region',
    'Акимат': 'akimat',
    'Направление водства': 'direction',
    'Наименование субсидирования': 'subsidy_type',
    'Норматив': 'normative',
    'Причитающая сумма': 'amount',
    'Район хозяйства': 'district',
    'БИН/ИИН': 'bin_iin',
}

COLUMN_DISPLAY_MAP = {v: k for k, v in COLUMN_RENAME_MAP.items()}
COLUMN_DISPLAY_MAP['bin_iin'] = 'БИН/ИИН'
COLUMN_DISPLAY_MAP['id'] = '№'
COLUMN_DISPLAY_MAP['score'] = 'AI Балл'
COLUMN_DISPLAY_MAP['category'] = 'Категория'
COLUMN_DISPLAY_MAP['probability'] = 'Вероятность'
COLUMN_DISPLAY_MAP['model_version'] = 'Версия модели'
COLUMN_DISPLAY_MAP['created_at'] = 'Дата оценки'
COLUMN_DISPLAY_MAP['status'] = 'Статус заявки'

REQUIRED_COLUMNS = [
    'submission_date', 'request_number',
    'direction', 'subsidy_type', 'status', 'normative', 'amount', 'district',
]

INFERENCE_REQUIRED_COLUMNS = [
    'direction', 'subsidy_type',
    'normative', 'amount', 'district',
]

TEMPLATE_COLUMNS = [
    'Направление водства',
    'Наименование субсидирования', 'Норматив',
    'Причитающая сумма', 'Район хозяйства', 'БИН/ИИН',
]

DATE_COLUMN = 'submission_date'

NUMERIC_COLUMNS = ['normative', 'amount']

CATEGORICAL_COLUMNS = [
    'direction', 'subsidy_type', 'status', 'district',
]

INFERENCE_CATEGORICAL_COLUMNS = [
    'direction', 'subsidy_type', 'district',
]

APPROVED_STATUSES = ['исполнена', 'одобрена']
REJECTED_STATUSES = ['отклонена', 'отозвано']
IN_PROGRESS_STATUSES = ['получена', 'сформировано поручение']

MODEL_PARAMS = {
    'n_estimators': 200,
    'max_depth': 6,
    'learning_rate': 0.05,
    'random_state': 42,
    'n_jobs': -1,
    'verbose': -1,
    'is_unbalance': True,
    'min_child_samples': 20,
    'reg_alpha': 0.1,
    'reg_lambda': 1.0,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
}

SCORE_MIN = 0
SCORE_MAX = 100

# Базовое значение SHAP (центр шкалы 0-100)
SHAP_BASE_VALUE = 50

# Диапазон для сравнения по сумме (+-30% от суммы заявки)
PEER_AMOUNT_RANGE_FACTOR = 0.3

CATEGORY_DISPLAY = {
    'LOW': 'Низкий приоритет',
    'MEDIUM': 'Средний приоритет',
    'HIGH': 'Высокий приоритет',
}

FEATURE_DISPLAY_NAMES = {
    'amount': 'Причитающая сумма',
    'normative': 'Норматив',
    'district': 'Район',
    'subsidy_type': 'Вид субсидии',
    'direction': 'Направление',
    'amount_to_normative': 'Расчетное поголовье',
    'approval_rate_district': 'Историческая одобряемость района',
    'approval_rate_subsidy_type': 'Историческая одобряемость субсидии',
    'amount_rank_in_subsidy_type': 'Размер среди аналогичных субсидий',
    'log_amount': 'Причитающая сумма',
}

MERGE_FEATURES = {
    'amount': 'Причитающая сумма',
    'log_amount': 'Причитающая сумма',
}

API_TITLE = "AgriScore System"
API_VERSION = "1.0.0"
