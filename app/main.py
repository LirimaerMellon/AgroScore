"""
Точка входа FastAPI приложения AgriScore.
Содержит конфигурацию CORS, подключение роутеров,
JSON-сериализацию numpy-типов и health-check.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import json
import logging

import numpy as np

from app.config import DB_PATH, API_TITLE, API_VERSION
from app.database import Database, ModelRepository
from app.routers import (
    train, score, template, applications,
    analytics, errors, models_rt, export, shortlist, thresholds,
)


def _sanitize_value(v):
    """Заменяет float NaN/Inf на None."""
    if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
        return None
    return v


def _sanitize_recursive(obj):
    """Рекурсивно заменяет NaN/Inf на None в произвольной структуре."""
    if isinstance(obj, dict):
        return {k: _sanitize_recursive(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_recursive(v) for v in obj]
    return _sanitize_value(obj)


class NumpyEncoder(json.JSONEncoder):
    """JSON encoder, поддерживающий numpy типы (NaN/Inf -> null)."""
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            v = float(obj)
            return _sanitize_value(v)
        if isinstance(obj, np.ndarray):
            return _sanitize_recursive(obj.tolist())
        if isinstance(obj, np.bool_):
            return bool(obj)
        return super().default(obj)


class NumpyJSONResponse(JSONResponse):
    """JSONResponse с поддержкой numpy типов и NaN -> null."""

    def render(self, content) -> bytes:
        content = _sanitize_recursive(content)
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            cls=NumpyEncoder,
        ).encode("utf-8")


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

_db: Database | None = None


def get_db() -> Database:
    global _db
    if _db is None:
        _db = Database(str(DB_PATH))
        _db.init_schema()
    return _db


app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    default_response_class=NumpyJSONResponse,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

get_db()

app.include_router(train.router)
app.include_router(score.router)
app.include_router(template.router)
app.include_router(applications.router)
app.include_router(analytics.router)
app.include_router(errors.router)
app.include_router(models_rt.router)
app.include_router(export.router)
app.include_router(shortlist.router)
app.include_router(thresholds.router)


@app.get("/health")
def health_check():
    db = get_db()
    model_repo = ModelRepository(db)
    active = model_repo.get_active()

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "model_loaded": active is not None,
        "active_model": active["version"] if active else None,
    }
