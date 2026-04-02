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
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Лог ошибок очистки данных. Каждая запись — невалидная строка из исходного файла."""
    repo = _repo()
    if trace_id:
        items = repo.get_by_trace(trace_id, limit=limit, offset=offset)
    else:
        items = repo.get_all(limit=limit, offset=offset)

    total = repo.count(trace_id=trace_id or None)

    return {"total": total, "items": items}


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
