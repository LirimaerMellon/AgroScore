from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

import logging
from datetime import datetime
import pandas as pd

from app.config import RAW_DATA_DIR, MODELS_DIR, COLUMN_RENAME_MAP
from app.pipeline import (
    load_data, validate_columns, clean_data, add_target_variable,
    FeatureEngineer, ScoringModel, FeatureExplainer
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


app = FastAPI(
    title="AgriScore",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class AppState:
    raw_data: pd.DataFrame = None
    cleaned_data: pd.DataFrame = None
    enriched_data: pd.DataFrame = None
    scored_data: pd.DataFrame = None
    model: ScoringModel = None
    explainer: FeatureExplainer = None
    feature_engineer: FeatureEngineer = None


state = AppState()

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "model_loaded": state.model is not None
    }

@app.post("/api/v1/upload")
async def upload_excel(file: UploadFile = File(...)):
    logger.info(f"Загрузка файла: {file.filename}")

    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Поддерживает только excel файлы")

    try:
        file_path = RAW_DATA_DIR / f"{datetime.now().timestamp()}_{file.filename}"
        with open(file_path, "wb") as f:
            f.write(await file.read())

        df = load_data(str(file_path))

        df = df.rename(columns=COLUMN_RENAME_MAP)

        is_valid, issues = validate_columns(df)
        if not is_valid:
            raise HTTPException(status_code=400, detail=str(issues))

        state.raw_data = df

        logger.info("Чистим данные...")
        state.cleaned_data = clean_data(state.raw_data)

        state.cleaned_data = add_target_variable(state.cleaned_data)

        logger.info("В процессе...")
        state.feature_engineer = FeatureEngineer(state.cleaned_data)
        state.feature_engineer.calculate_approval_rates()
        state.feature_engineer.calculate_financial_aggregates()
        state.enriched_data = state.feature_engineer.enrich_dataset()

        logger.info("Тренируем модель...")
        state.model = ScoringModel()
        metrics = state.model.train(state.enriched_data)

        state.scored_data = state.model.score(state.enriched_data)
        state.scored_data = state.scored_data.sort_values("score", ascending=False)

        state.explainer = FeatureExplainer(
            state.model.model,
            state.model.feature_names
        )

        model_path = MODELS_DIR / f"model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
        state.model.save(str(model_path))

        logger.info("Успешно завершено")

        return {
            "status": "success",
            "total_records": len(state.raw_data),
            "cleaned_records": len(state.cleaned_data),
            "model_metrics": metrics
        }

    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/shortlist")
async def get_shortlist(limit: int = 50):

    if state.scored_data is None:
        raise HTTPException(status_code=400, detail="Данные еще не обработаны")

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
            logger.warning(f"Ошибка: {e}")
            item["top_factors"] = None

    return {
        "total": len(state.scored_data),
        "shortlist_size": len(shortlist),
        "shortlist": shortlist
    }


@app.get("/api/v1/analytics")
async def analytics():

    if state.scored_data is None:
        raise HTTPException(status_code=400, detail="Данные не обработаны")

    df = state.scored_data

    return {
        "total": len(df),
        "mean_score": float(df["score"].mean()),
        "median_score": float(df["score"].median()),
        "min_score": float(df["score"].min()),
        "max_score": float(df["score"].max()),
        "high": int((df["score"] >= 70).sum()),
        "medium": int(((df["score"] >= 40) & (df["score"] < 70)).sum()),
        "low": int((df["score"] < 40).sum())
    }


@app.get("/api/v1/export")
async def export():

    if state.scored_data is None:
        raise HTTPException(status_code=400, detail="Данные не обработаны")

    output_path = MODELS_DIR / f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    state.scored_data.to_excel(output_path, index=False)

    return FileResponse(
        output_path,
        filename=output_path.name
    )