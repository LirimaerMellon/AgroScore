"""
Pydantic-схемы для всех API эндпоинтов AgriScore.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any


# =========================
# COMMON
# =========================

class TopFactor(BaseModel):
    feature: str
    value: float
    importance: float
    direction: str


# =========================
# TRAINING
# =========================

class TrainResponse(BaseModel):
    status: str
    model_version: str
    total_raw_records: int
    cleaned_records: int
    metrics: Dict[str, Any]
    fairness: Dict[str, Any]
    feature_importance: List[Dict[str, Any]]
    trace_id: Optional[str] = None


class TrainJsonRecord(BaseModel):
    """Одна запись для обучения (JSON формат)."""
    submission_date: Optional[str] = Field(None, alias="Дата поступления")
    region: Optional[str] = Field(None, alias="Область")
    akimat: Optional[str] = Field(None, alias="Акимат")
    request_number: Optional[str] = Field(None, alias="Номер заявки")
    direction: Optional[str] = Field(None, alias="Направление водства")
    subsidy_type: Optional[str] = Field(None, alias="Наименование субсидирования")
    status: Optional[str] = Field(None, alias="Статус заявки")
    normative: Optional[float] = Field(None, alias="Норматив")
    amount: Optional[float] = Field(None, alias="Причитающая сумма")
    district: Optional[str] = Field(None, alias="Район хозяйства")

    model_config = {"populate_by_name": True}


class TrainJsonRequest(BaseModel):
    records: List[TrainJsonRecord]
    model_version: Optional[str] = None


# =========================
# SCORING
# =========================

class ScoreJsonRecord(BaseModel):
    """Одна запись для скоринга (JSON формат)."""
    region: Optional[str] = Field(None, alias="Область")
    akimat: Optional[str] = Field(None, alias="Акимат")
    direction: Optional[str] = Field(None, alias="Направление водства")
    subsidy_type: Optional[str] = Field(None, alias="Наименование субсидирования")
    normative: Optional[float] = Field(None, alias="Норматив")
    amount: Optional[float] = Field(None, alias="Причитающая сумма")
    district: Optional[str] = Field(None, alias="Район хозяйства")
    bin_iin: Optional[str] = Field(None, alias="БИН/ИИН")

    model_config = {"populate_by_name": True}


class ScoreJsonRequest(BaseModel):
    applications: List[ScoreJsonRecord]
    model_version: Optional[str] = None


class ScoredApplication(BaseModel):
    id: Optional[int] = None
    model_version: str
    bin_iin: Optional[str] = None
    region: Optional[str] = None
    akimat: Optional[str] = None
    direction: Optional[str] = None
    subsidy_type: Optional[str] = None
    normative: Optional[float] = None
    amount: Optional[float] = None
    district: Optional[str] = None
    score: float
    category: str
    probability: float
    shap_explanation: Optional[Dict[str, Any]] = None


class ScoreResponse(BaseModel):
    status: str
    model_version: str
    total_raw: int
    total_scored: int
    trace_id: Optional[str] = None
    categories: Dict[str, int]
    applications: List[ScoredApplication]


# =========================
# APPLICATIONS
# =========================

class ApplicationListResponse(BaseModel):
    total: int
    items: List[Dict[str, Any]]


class ApplicationDetailResponse(BaseModel):
    application: Dict[str, Any]


# =========================
# ANALYTICS
# =========================

class AnalyticsSummary(BaseModel):
    total: int
    mean_score: Optional[float] = 0
    min_score: Optional[float] = 0
    max_score: Optional[float] = 0
    high: int = 0
    medium: int = 0
    low: int = 0


class ScoreDistributionBin(BaseModel):
    range: str
    count: int


class FeatureImportanceItem(BaseModel):
    feature: str
    importance: float


# =========================
# MODELS
# =========================

class ModelInfo(BaseModel):
    id: int
    version: str
    created_at: str
    file_path: str
    metrics: Dict[str, Any]
    train_size: int
    n_features: int
    positive_rate: float
    is_active: int


# =========================
# ERROR LOG
# =========================

class Violation(BaseModel):
    code: str
    cols: List[str]
    msg: str
    display: str


class ErrorLogItem(BaseModel):
    id: int
    trace_id: str
    detected_at: str
    source_type: str
    source_name: str
    error_codes: List[str]
    error_cols: List[str]
    locator: Dict[str, Any]
    raw_payload: Optional[Dict[str, Any]] = None
    violations: List[Any]


class ErrorLogResponse(BaseModel):
    total: int
    items: List[Dict[str, Any]]


class ErrorSummaryResponse(BaseModel):
    total_errors: int
    by_error_code: Dict[str, int]
    by_column: Dict[str, int]


class TraceListItem(BaseModel):
    trace_id: str
    source_name: str
    source_type: str
    first_detected: str
    error_count: int


class TraceListResponse(BaseModel):
    traces: List[TraceListItem]