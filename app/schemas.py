from pydantic import BaseModel
from typing import List, Dict, Optional

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
    model_metrics: Dict[str, float]


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