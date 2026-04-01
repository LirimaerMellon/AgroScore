"""
Модуль конфигурации проекта AgriScore System.

Назначение:
- Пути к данным и артефактам
- Настройки входных данных
- Описание колонок
- Бизнес-правила (статусы)
- Параметры ML модели
- Настройки API

Используется как единый источник конфигурации во всем пайплайне.
"""

from pathlib import Path

# =========================
# БАЗОВЫЕ ПУТИ
# =========================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"

RAW_DATA_DIR = DATA_DIR / "raw"
MODELS_DIR = DATA_DIR / "models"
DEBUG_DIR = DATA_DIR / "debug"
RESULTS_DIR = DATA_DIR / "results"
FEATURES_DIR = DATA_DIR / "features"

# =========================
# БАЗА ДАННЫХ
# =========================

DB_PATH = DATA_DIR / "agriscore.db"

# =========================
# ВЕРСИЯ МОДЕЛИ
# =========================

MODEL_VERSION = "v1"

MODEL_DIR = MODELS_DIR / MODEL_VERSION
MODEL_PATH = MODEL_DIR / "model.pkl"
FEATURES_PATH = MODEL_DIR / "features.pkl"

# =========================
# КОЛОНКИ (EXCEL → INTERNAL)
# =========================

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
    'Район хозяйства': 'district'
}

# =========================
# ОБРАТНЫЙ МАППИНГ КОЛОНОК (internal → display)
# =========================

COLUMN_DISPLAY_MAP = {v: k for k, v in COLUMN_RENAME_MAP.items()}

# =========================
# ОБЯЗАТЕЛЬНЫЕ КОЛОНКИ
# =========================

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

# =========================
# ТИПЫ ПРИЗНАКОВ
# =========================

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

# =========================
# БИЗНЕС-ЛОГИКА (СТАТУСЫ)
# =========================

APPROVED_STATUSES = [
    'исполнена',
    'одобрена'
]

REJECTED_STATUSES = [
    'отклонена',
    'отозвано'
]

IN_PROGRESS_STATUSES = [
    'получена',
    'сформировано получение'
]

# =========================
# FEATURE ENGINEERING
# =========================

DERIVED_FEATURES = [
    'amount_to_normative',
    'log_amount',
    'log_normative',
    'days_since_submission',
    'month',
    'quarter',
    'day_of_week',
    'day'
]

# =========================
# ПАРАМЕТРЫ МОДЕЛИ
# =========================

MODEL_PARAMS = {
    'n_estimators': 200,
    'max_depth': 6,
    'learning_rate': 0.05,
    'random_state': 42,
    'n_jobs': -1,
    'verbose': -1
}

# =========================
# ДИАПАЗОН СКОРИНГА
# =========================

SCORE_MIN = 0
SCORE_MAX = 100

# =========================
# API
# =========================

API_TITLE = "AgriScore System"
API_VERSION = "1.0.0"