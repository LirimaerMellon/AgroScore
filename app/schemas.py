from pydantic import BaseModel
from typing import List, Dict, Optional, Any


class TopFactor(BaseModel):
    feature: str
    value: float
    importance: float
    direction: str


class UploadResponse(BaseModel):
    status: str
    message: str
    total_records: int
    cleaned_records: int
    model_metrics: Dict[str, Any]
    trace_id: Optional[str] = None


class ScoreDetail(BaseModel):
    request_number: str
    score: float
    category: str
    probability: float
    top_factors: List[TopFactor]


class ShortlistItem(BaseModel):
    request_number: str
    score: float
    category: str
    probability: float
    region: Optional[str] = None
    subsidy_type: Optional[str] = None
    amount: Optional[float] = None
    top_factors: Optional[List[TopFactor]] = None


class ShortlistResponse(BaseModel):
    total_applications: int
    shortlist_size: int
    shortlist: List[ShortlistItem]
    summary: Dict[str, float]


# =========================
# ERROR LOG SCHEMAS
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
    violations: List[Violation]


class ErrorLogResponse(BaseModel):
    total: int
    items: List[ErrorLogItem]


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