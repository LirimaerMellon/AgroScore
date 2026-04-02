"""
POST /api/score        — скоринг заявок из файла (Excel/CSV)
POST /api/score/json   — скоринг заявок из JSON body
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
import logging
import io
import pandas as pd

from app.database import ErrorLogRepository, ModelRepository, ApplicationRepository
from app.services.scoring import ScoringService
from app.pipeline.loader import DataLoader
from app.schemas import ScoreJsonRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["scoring"])


def _get_service():
    from app.main import get_db
    db = get_db()
    return ScoringService(
        error_repo=ErrorLogRepository(db),
        model_repo=ModelRepository(db),
        app_repo=ApplicationRepository(db),
    )


@router.post("/score")
def score_applications(
    file: UploadFile = File(...),
    model_version: Optional[str] = Form(None),
):
    """Скоринг заявок из Excel/CSV файла (по шаблону)."""
    allowed = (".xlsx", ".xls", ".csv")
    if not file.filename.endswith(allowed):
        raise HTTPException(400, f"Допустимые форматы: {allowed}")

    try:
        content = file.file.read()
        buf = io.BytesIO(content)

        loader = DataLoader(required_columns=[])
        df = loader.load_from_buffer(buf, filename=file.filename)
        source_type = "csv" if file.filename.endswith(".csv") else "excel"

        result = _get_service().score(
            df=df, source_name=file.filename,
            source_type=source_type, model_version=model_version,
        )
        return result

    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Ошибка скоринга: {e}", exc_info=True)
        raise HTTPException(500, str(e))


@router.post("/score/json")
def score_applications_json(request: ScoreJsonRequest):
    """Скоринг заявок из JSON body."""
    try:
        records = [r.model_dump(by_alias=False) for r in request.applications]
        df = pd.DataFrame(records)

        result = _get_service().score(
            df=df, source_name="json_upload",
            source_type="json", model_version=request.model_version,
        )
        return result

    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Ошибка скоринга: {e}", exc_info=True)
        raise HTTPException(500, str(e))
