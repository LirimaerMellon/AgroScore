"""
GET    /api/models           — список обученных моделей
POST   /api/models/activate  — активировать конкретную модель
DELETE /api/admin/reset       — полная очистка БД и удаление файлов моделей
"""

from fastapi import APIRouter, HTTPException, Query
from pathlib import Path
import logging

from app.database import ModelRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["models"])


def _repo():
    from app.main import get_db
    return ModelRepository(get_db())


@router.get("/models")
def list_models(limit: int = Query(50, ge=1, le=200)):
    """Список обученных моделей (новые первые)."""
    models = _repo().get_all(limit=limit)
    return {"total": len(models), "models": models}


@router.post("/models/activate")
def activate_model(version: str = Query(...)):
    """Сделать указанную модель активной (используется при скоринге)."""
    success = _repo().activate(version)
    if not success:
        raise HTTPException(404, f"Модель {version} не найдена")
    return {"status": "success", "active_version": version}


@router.delete("/admin/reset")
def reset_database(
    applications: bool = Query(True, description="Очистить таблицу заявок"),
    models: bool = Query(True, description="Очистить модели (БД + файлы .pkl)"),
    errors: bool = Query(True, description="Очистить лог ошибок"),
):
    """
    Полный сброс системы.

    Удаляет данные из выбранных таблиц и файлы моделей с диска.
    После сброса потребуется заново обучить модель через POST /api/train.
    """
    from app.main import get_db

    db = get_db()
    deleted: dict = {}

    with db.get_connection() as conn:
        if applications:
            count = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
            conn.execute("DELETE FROM applications")
            deleted["applications"] = count

        if models:
            # Собираем пути к файлам моделей до удаления записей
            rows = conn.execute("SELECT file_path FROM models").fetchall()
            count = conn.execute("SELECT COUNT(*) FROM models").fetchone()[0]
            conn.execute("DELETE FROM models")
            deleted["models"] = count

            # Удаляем .pkl файлы с диска
            files_removed = 0
            for row in rows:
                p = Path(row["file_path"])
                if p.exists():
                    try:
                        p.unlink()
                        files_removed += 1
                    except OSError as e:
                        logger.warning(f"Не удалось удалить {p}: {e}")
            deleted["model_files_removed"] = files_removed

        if errors:
            count = conn.execute("SELECT COUNT(*) FROM error_logs").fetchone()[0]
            conn.execute("DELETE FROM error_logs")
            deleted["error_logs"] = count

    logger.info(f"БД очищена: {deleted}")

    return {
        "status": "success",
        "message": "База данных очищена. Обучите модель заново через POST /api/train.",
        "deleted": deleted,
    }


