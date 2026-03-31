from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
MODELS_DIR = DATA_DIR / "models"

# Создание директорий при необходимости
for directory in [RAW_DATA_DIR, MODELS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

COLUMN_RENAME_MAP = {
    'n': 'id',
    'date': 'submission_date',
    'region': 'region',
    'akimat': 'akimat',
    'request number': 'request_number',
    'direction': 'direction',
    'subsidy_type': 'subsidy_type',
    'status': 'status',
    'normative': 'normative',
    'amount': 'amount',
    'district': 'district'
}

REQUIRED_COLUMNS = [
    'submission_date',
    'region',
    'akimat',
    'request_number',
    'direction',
    'subsidy_type',
    'status',
    'normative',
    'amount',
    'district'
]

DATE_COLUMN = 'submission_date'

NUMERIC_COLUMNS = [
    'normative',
    'amount'
]

CATEGORICAL_COLUMNS = [
    'region',
    'akimat',
    'direction',
    'subsidy_type',
    'status',
    'district'
]

ID_COLUMN = 'id'

DERIVED_FEATURES = [
    'amount_to_normative',
    'month',
    'day_of_week',
    'hour'
]

MODEL_PARAMS = {
    'n_estimators': 200,
    'max_depth': 6,
    'learning_rate': 0.05,
    'random_state': 42,
    'n_jobs': -1,
    'verbose': -1
}

MODEL_PATH = MODELS_DIR / "model.pkl"
FEATURES_PATH = MODELS_DIR / "features.pkl"

SCORE_MIN = 0
SCORE_MAX = 100

API_TITLE = "Agricultural Subsidy Scoring API"
API_VERSION = "1.0.0"