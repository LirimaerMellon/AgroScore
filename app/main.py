"""
FastAPI приложение AgriScore.

Эндпоинты:
- POST /api/v1/upload     — загрузка Excel, обучение модели
- GET  /api/v1/shortlist   — топ-N заявителей с SHAP-объяснениями
- GET  /api/v1/analytics   — общая аналитика скоров
- GET  /api/v1/fairness    — fairness-отчёт по группам
- GET  /api/v1/errors      — лог ошибок очистки данных
- GET  /api/v1/errors/summary — сводка ошибок
- GET  /api/v1/errors/traces  — список загрузок
- GET  /api/v1/export      — экспорт результатов в Excel
- GET  /health             — health-check
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

import logging
from datetime import datetime
import pandas as pd

from app.config import RAW_DATA_DIR, MODELS_DIR, COLUMN_RENAME_MAP, DB_PATH
from app.database import Database, ErrorLogRepository
from app.pipeline import (
    DataLoader, DataCleaner,
    FeatureEngineer, ScoringModel, FeatureExplainer,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# =========================
# APP INIT
# =========================

app = FastAPI(title="AgriScore", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# DATABASE
# =========================

db = Database(str(DB_PATH))
db.init_schema()
error_repo = ErrorLogRepository(db)

# =========================
# STATE
# =========================

class AppState:
    raw_data: pd.DataFrame = None
    cleaned_data: pd.DataFrame = None
    enriched_data: pd.DataFrame = None
    scored_data: pd.DataFrame = None
    model: ScoringModel = None
    explainer: FeatureExplainer = None
    feature_engineer: FeatureEngineer = None
    last_trace_id: str = None
    last_metrics: dict = None
    last_fairness: dict = None


state = AppState()

# =========================
# ENDPOINTS
# =========================

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "model_loaded": state.model is not None,
    }


@app.post("/api/v1/upload")
async def upload_excel(file: UploadFile = File(...)):
    logger.info(f"Загрузка файла: {file.filename}")

    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Поддерживаются только Excel файлы (.xlsx/.xls)")

    try:
        # --- Сохранение файла ---
        file_path = RAW_DATA_DIR / f"{datetime.now().timestamp()}_{file.filename}"
        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(await file.read())

        # --- Загрузка ---
        loader = DataLoader()
        df = loader.load_data(str(file_path))
        df = df.rename(columns=COLUMN_RENAME_MAP)
        loader.validate_columns(df)
        state.raw_data = df

        # --- Очистка с логированием ошибок ---
        cleaner = DataCleaner(error_repo=error_repo)
        state.cleaned_data = cleaner.clean_data(
            state.raw_data,
            source_name=file.filename,
            source_type="excel",
        )
        state.cleaned_data = cleaner.add_target_variable(
            state.cleaned_data,
            source_name=file.filename,
            source_type="excel",
        )
        state.last_trace_id = cleaner.last_trace_id

        # --- Feature engineering ---
        logger.info("Feature engineering...")
        state.feature_engineer = FeatureEngineer(state.cleaned_data)
        state.feature_engineer.calculate_approval_rates()
        state.feature_engineer.calculate_financial_aggregates()
        state.enriched_data = state.feature_engineer.enrich_dataset()

        # --- Обучение ---
        logger.info("Тренируем модель...")
        state.model = ScoringModel()
        state.last_metrics = state.model.train(state.enriched_data)

        # --- Скоринг ---
        state.scored_data = state.model.score(state.enriched_data)
        state.scored_data = state.scored_data.sort_values("score", ascending=False)

        # --- Fairness ---
        state.last_fairness = state.model.compute_fairness_report(state.scored_data)

        # --- Explainer ---
        state.explainer = FeatureExplainer(
            state.model.model,
            state.model.feature_names,
            state.enriched_data[state.model.feature_names],
        )

        # --- Сохранение модели ---
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        model_path = MODELS_DIR / f"model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
        state.model.save(str(model_path))

        logger.info("Успешно завершено")

        return {
            "status": "success",
            "total_records": len(state.raw_data),
            "cleaned_records": len(state.cleaned_data),
            "model_metrics": state.last_metrics,
            "trace_id": state.last_trace_id,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/shortlist")
async def get_shortlist(limit: int = 50):
    if state.scored_data is None:
        raise HTTPException(status_code=400, detail="Данные ещё не обработаны")

    shortlist_df = state.scored_data.head(limit)
    shortlist = shortlist_df.to_dict(orient="records")

    for item in shortlist[:10]:
        try:
            row = shortlist_df[
                shortlist_df["request_number"] == item["request_number"]
            ]
            if row.empty:
                continue

            X_single = row[state.model.feature_names]
            explanation = state.explainer.explain_single(X_single)
            item["top_factors"] = explanation["top_factors"]

        except Exception as e:
            logger.warning(f"SHAP explain error: {e}")
            item["top_factors"] = None

    return {
        "total": len(state.scored_data),
        "shortlist_size": len(shortlist),
        "shortlist": shortlist,
    }


@app.get("/api/v1/analytics")
async def analytics():
    if state.scored_data is None:
        raise HTTPException(status_code=400, detail="Данные не обработаны")

    df = state.scored_data
    return {
        "total": len(df),
        "mean_score": round(float(df["score"].mean()), 2),
        "median_score": round(float(df["score"].median()), 2),
        "min_score": round(float(df["score"].min()), 2),
        "max_score": round(float(df["score"].max()), 2),
        "high": int((df["category"] == "HIGH").sum()),
        "medium": int((df["category"] == "MEDIUM").sum()),
        "low": int((df["category"] == "LOW").sum()),
        "model_metrics": state.last_metrics,
    }


@app.get("/api/v1/fairness")
async def fairness():
    """Fairness-отчёт: распределение скоров по регионам / типам субсидий."""
    if state.last_fairness is None:
        raise HTTPException(status_code=400, detail="Данные не обработаны")

    return state.last_fairness


# =========================
# ERROR LOG ENDPOINTS
# =========================

@app.get("/api/v1/errors")
async def get_errors(
    trace_id: str = Query(None, description="Фильтр по trace_id загрузки"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """
    Лог ошибок очистки данных.
    Каждая запись — одна невалидная строка из исходного файла.
    """
    if trace_id:
        items = error_repo.get_by_trace(trace_id)
    else:
        items = error_repo.get_all(limit=limit, offset=offset)

    return {"total": len(items), "items": items}


@app.get("/api/v1/errors/summary")
async def get_error_summary(
    trace_id: str = Query(None, description="Фильтр по trace_id загрузки"),
):
    """Сводка: сколько ошибок, по каким кодам, по каким колонкам."""
    return error_repo.get_summary(trace_id)


@app.get("/api/v1/errors/traces")
async def get_traces(limit: int = Query(50, ge=1, le=500)):
    """Список загрузок с числом ошибок в каждой."""
    return {"traces": error_repo.get_traces(limit)}


# =========================
# EXPORT
# =========================

@app.get("/api/v1/export")
async def export():
    if state.scored_data is None:
        raise HTTPException(status_code=400, detail="Данные не обработаны")

    output_path = MODELS_DIR / f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    state.scored_data.to_excel(output_path, index=False)

    return FileResponse(output_path, filename=output_path.name)