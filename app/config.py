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
# КОЛОНКИ (EXCEL → INTERNAL) — ОБУЧЕНИЕ
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
    'Район хозяйства': 'district',
}

# =========================
# КОЛОНКИ (EXCEL → INTERNAL) — INFERENCE (шаблон)
# =========================

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

# =========================
# ОБРАТНЫЙ МАППИНГ КОЛОНОК (internal → display)
# =========================

COLUMN_DISPLAY_MAP = {v: k for k, v in COLUMN_RENAME_MAP.items()}
COLUMN_DISPLAY_MAP['bin_iin'] = 'БИН/ИИН'
COLUMN_DISPLAY_MAP['id'] = '№'
COLUMN_DISPLAY_MAP['score'] = 'AI Балл'
COLUMN_DISPLAY_MAP['category'] = 'Категория'
COLUMN_DISPLAY_MAP['probability'] = 'Вероятность'
COLUMN_DISPLAY_MAP['model_version'] = 'Версия модели'
COLUMN_DISPLAY_MAP['created_at'] = 'Дата оценки'
COLUMN_DISPLAY_MAP['status'] = 'Статус заявки'

# =========================
# ОБЯЗАТЕЛЬНЫЕ КОЛОНКИ
# =========================

REQUIRED_COLUMNS = [
    'submission_date', 'region', 'akimat', 'request_number',
    'direction', 'subsidy_type', 'status', 'normative', 'amount', 'district',
]

INFERENCE_REQUIRED_COLUMNS = [
    'region', 'akimat', 'direction', 'subsidy_type',
    'normative', 'amount', 'district',
]

# =========================
# ШАБЛОН ДЛЯ СКАЧИВАНИЯ (русские заголовки)
# =========================

TEMPLATE_COLUMNS = [
    'Область', 'Акимат', 'Направление водства',
    'Наименование субсидирования', 'Норматив',
    'Причитающая сумма', 'Район хозяйства', 'БИН/ИИН',
]

# =========================
# ТИПЫ ПРИЗНАКОВ
# =========================

DATE_COLUMN = 'submission_date'

NUMERIC_COLUMNS = ['normative', 'amount']

CATEGORICAL_COLUMNS = [
    'region', 'akimat', 'direction', 'subsidy_type', 'status', 'district',
]

INFERENCE_CATEGORICAL_COLUMNS = [
    'region', 'akimat', 'direction', 'subsidy_type', 'district',
]

# =========================
# БИЗНЕС-ЛОГИКА (СТАТУСЫ)
# =========================

APPROVED_STATUSES = ['исполнена', 'одобрена']
REJECTED_STATUSES = ['отклонена', 'отозвано']
IN_PROGRESS_STATUSES = ['получена', 'сформировано поручение']

# =========================
# FEATURE ENGINEERING
# =========================

DERIVED_FEATURES = [
    'amount_to_normative', 'log_amount', 'log_normative',
    'unknown_ratio',
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
    'verbose': -1,
    'is_unbalance': True,
    'min_child_samples': 20,
    'reg_alpha': 0.1,
    'reg_lambda': 1.0,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
}

# =========================
# ДИАПАЗОН СКОРИНГА
# =========================

SCORE_MIN = 0
SCORE_MAX = 100

# =========================
# ЧЕЛОВЕКОЧИТАЕМЫЕ НАЗВАНИЯ ПРИЗНАКОВ (для SHAP)
# =========================

FEATURE_DISPLAY_NAMES = {
    'region': 'Область',
    'akimat': 'Акимат',
    'direction': 'Направление',
    'subsidy_type': 'Вид субсидии',
    'normative': 'Норматив (₸)',
    'amount': 'Причитающаяся сумма (₸)',
    'district': 'Район',
    'bin_iin': 'БИН/ИИН',
    'approval_rate_region': 'Ист. одобрение (область)',
    'approval_rate_subsidy_type': 'Ист. одобрение (вид субсидии)',
    'approval_rate_direction': 'Ист. одобрение (направление)',
    'approval_rate_district': 'Ист. одобрение (район)',
    'approval_rate_akimat': 'Ист. одобрение (акимат)',
    'amount_to_normative': 'Сумма / Норматив',
    'log_amount': 'Лог суммы',
    'log_normative': 'Лог норматива',
    'days_since_submission': 'Дней с подачи',
    'month': 'Месяц подачи',
    'quarter': 'Квартал',
    'day_of_week': 'День недели',
    'day': 'День месяца',
    'amount_rank_in_region': 'Ранг суммы (область)',
    'amount_rank_in_subsidy_type': 'Ранг суммы (вид субсидии)',
    'amount_rank_in_direction': 'Ранг суммы (направление)',
    'amount_zscore_region': 'Отклонение суммы (область)',
    'amount_zscore_subsidy_type': 'Отклонение суммы (вид субсидии)',
    'region_x_direction': 'Область × Направление',
    'region_x_subsidy_type': 'Область × Вид субсидии',
    'sum_amount_region': 'Общая сумма (область)',
    'mean_amount_region': 'Средняя сумма (область)',
    'median_amount_region': 'Медиана суммы (область)',
    'std_amount_region': 'Разброс суммы (область)',
    'count_region': 'Кол-во заявок (область)',
    'sum_amount_subsidy_type': 'Общая сумма (вид субсидии)',
    'mean_amount_subsidy_type': 'Средняя сумма (вид субсидии)',
    'median_amount_subsidy_type': 'Медиана суммы (вид субсидии)',
    'std_amount_subsidy_type': 'Разброс суммы (вид субсидии)',
    'count_subsidy_type': 'Кол-во заявок (вид субсидии)',
    'sum_amount_direction': 'Общая сумма (направление)',
    'mean_amount_direction': 'Средняя сумма (направление)',
    'median_amount_direction': 'Медиана суммы (направление)',
    'std_amount_direction': 'Разброс суммы (направление)',
    'count_direction': 'Кол-во заявок (направление)',
    'sum_amount_district': 'Общая сумма (район)',
    'mean_amount_district': 'Средняя сумма (район)',
    'median_amount_district': 'Медиана суммы (район)',
    'std_amount_district': 'Разброс суммы (район)',
    'count_district': 'Кол-во заявок (район)',
    'sum_amount_akimat': 'Общая сумма (акимат)',
    'mean_amount_akimat': 'Средняя сумма (акимат)',
    'median_amount_akimat': 'Медиана суммы (акимат)',
    'std_amount_akimat': 'Разброс суммы (акимат)',
    'count_akimat': 'Кол-во заявок (акимат)',
    'mean_normative_region': 'Средний норматив (область)',
    'mean_normative_subsidy_type': 'Средний норматив (вид субсидии)',
    'mean_normative_direction': 'Средний норматив (направление)',
    'mean_normative_district': 'Средний норматив (район)',
    'mean_normative_akimat': 'Средний норматив (акимат)',
    'unknown_ratio': 'Доля неизвестных полей',
}

# =========================
# API
# =========================

API_TITLE = "AgriScore System"
API_VERSION = "1.0.0"

