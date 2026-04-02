"""
POST /api/train        — загрузка файла (Excel/CSV) и обучение модели
POST /api/train/json   — обучение из JSON body
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
import logging
import io
import pandas as pd

from app.database import ErrorLogRepository, ModelRepository
from app.services.training import TrainingService
from app.pipeline.loader import DataLoader
from app.schemas import TrainJsonRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["training"])


def _get_service():
    from app.main import get_db
    db = get_db()
    return TrainingService(
        error_repo=ErrorLogRepository(db),
        model_repo=ModelRepository(db),
    )


@router.post("/train")
def train_model(
    file: UploadFile = File(...),
    model_version: Optional[str] = Form(None),
):
    """Обучение модели из Excel/CSV файла."""
    allowed = (".xlsx", ".xls", ".csv")
    if not file.filename.endswith(allowed):
        raise HTTPException(400, f"Допустимые форматы: {allowed}")

    try:
        content = file.file.read()
        buf = io.BytesIO(content)

        loader = DataLoader(required_columns=[])
        df = loader.load_from_buffer(buf, filename=file.filename)
        source_type = "csv" if file.filename.endswith(".csv") else "excel"

        result = _get_service().train(
            df=df, source_name=file.filename,
            source_type=source_type, model_version=model_version,
        )
        return result

    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Ошибка обучения: {e}", exc_info=True)
        raise HTTPException(500, str(e))


@router.post("/train/json")
def train_model_json(request: TrainJsonRequest):
    """Обучение модели из JSON body."""
    try:
        records = [r.model_dump(by_alias=False) for r in request.records]
        df = pd.DataFrame(records)

        result = _get_service().train(
            df=df, source_name="json_upload",
            source_type="json", model_version=request.model_version,
        )
        return result

    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Ошибка обучения: {e}", exc_info=True)
        raise HTTPException(500, str(e))
