"""
GET /api/errors          — лог невалидных строк
GET /api/errors/summary  — сводка ошибок
GET /api/errors/traces   — список загрузок с числом ошибок
"""

from fastapi import APIRouter, Query
from typing import Optional
import logging

from app.database import ErrorLogRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["errors"])


def _repo():
    from app.main import get_db
    return ErrorLogRepository(get_db())


@router.get("/errors")
def get_errors(
    trace_id: Optional[str] = Query(None, description="Фильтр по trace_id загрузки"),
    error_code: Optional[str] = Query(None, description="Фильтр по коду ошибки"),
    error_col: Optional[str] = Query(None, description="Фильтр по колонке"),
    source_name: Optional[str] = Query(None, description="Фильтр по имени источника"),
    sort_by: str = Query("detected_at", description="id|detected_at"),
    sort_dir: str = Query("desc", description="asc|desc"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Лог ошибок очистки данных. Каждая запись — невалидная строка из исходного файла."""
    repo = _repo()
    result = repo.get_filtered(
        trace_id=trace_id,
        error_code=error_code,
        error_col=error_col,
        source_name=source_name,
        sort_by=sort_by,
        sort_dir=sort_dir,
        limit=limit,
        offset=offset,
    )
    return result


@router.get("/errors/summary")
def get_error_summary(
    trace_id: Optional[str] = Query(None),
):
    """Сводка: сколько ошибок, по каким кодам, по каким колонкам."""
    return _repo().get_summary(trace_id)


@router.get("/errors/traces")
def get_traces(
    limit: int = Query(50, ge=1, le=500),
):
    """Список загрузок с числом ошибок в каждой."""
    return {"traces": _repo().get_traces(limit)}
