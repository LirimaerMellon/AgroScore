"""
FastAPI приложение AgriScore.

Система merit-based скоринга сельхозпроизводителей.

Эндпоинты:
  Обучение:
    POST /api/train          — обучение из Excel/CSV
    POST /api/train/json     — обучение из JSON

  Скоринг:
    POST /api/score          — скоринг заявок из Excel/CSV
    POST /api/score/json     — скоринг заявок из JSON
    GET  /api/template       — скачать Excel-шаблон

  Заявки:
    GET  /api/applications       — список оценённых заявок
    GET  /api/applications/{id}  — детали заявки + SHAP

  Аналитика:
    GET  /api/analytics/summary       — сводная статистика
    GET  /api/analytics/distribution  — гистограмма скоров
    GET  /api/analytics/features      — важность признаков
    GET  /api/analytics/fairness      — fairness-отчёт

  Модели:
    GET  /api/models            — список обученных моделей
    POST /api/models/activate   — активировать модель

  Ошибки:
    GET  /api/errors            — лог ошибок очистки
    GET  /api/errors/summary    — сводка ошибок
    GET  /api/errors/traces     — список загрузок

  Экспорт:
    GET  /api/export            — экспорт результатов в Excel

  Health:
    GET  /health                — health-check
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

# Роутеры
from app.routers import train, score, template, applications, analytics, errors, models_rt, export, shortlist


class NumpyEncoder(json.JSONEncoder):
    """JSON encoder, поддерживающий numpy типы (включая NaN/Inf → null)."""
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            v = float(obj)
            if np.isnan(v) or np.isinf(v):
                return None
            return v
        if isinstance(obj, np.ndarray):
            return self._sanitize_list(obj.tolist())
        if isinstance(obj, np.bool_):
            return bool(obj)
        return super().default(obj)

    @staticmethod
    def _sanitize_list(lst):
        """Заменяет NaN/Inf на None в списках (результат ndarray.tolist())."""
        result = []
        for v in lst:
            if isinstance(v, list):
                result.append(NumpyEncoder._sanitize_list(v))
            elif isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
                result.append(None)
            else:
                result.append(v)
        return result

class NumpyJSONResponse(JSONResponse):
    """JSONResponse с поддержкой numpy типов и NaN → null."""

    @staticmethod
    def _sanitize(obj):
        """Рекурсивно заменяет float NaN/Inf на None."""
        if isinstance(obj, dict):
            return {k: NumpyJSONResponse._sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [NumpyJSONResponse._sanitize(v) for v in obj]
        if isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
            return None
        return obj

    def render(self, content) -> bytes:
        content = self._sanitize(content)
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

# =========================
# DATABASE (singleton)
# =========================

_db: Database | None = None


def get_db() -> Database:
    global _db
    if _db is None:
        _db = Database(str(DB_PATH))
        _db.init_schema()
    return _db


# =========================
# APP FACTORY
# =========================

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

# Инициализация БД при старте
get_db()

# =========================
# ROUTERS
# =========================

app.include_router(train.router)
app.include_router(score.router)
app.include_router(template.router)
app.include_router(applications.router)
app.include_router(analytics.router)
app.include_router(errors.router)
app.include_router(models_rt.router)
app.include_router(export.router)
app.include_router(shortlist.router)

# =========================
# HEALTH CHECK
# =========================


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
