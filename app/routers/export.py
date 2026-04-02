"""
GET /api/export — экспорт оценённых заявок в Excel.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional
import io
import logging
import pandas as pd
from openpyxl.utils import get_column_letter

from app.database import ApplicationRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["export"])


def _repo():
    from app.main import get_db
    return ApplicationRepository(get_db())


# Колонки для экспорта: internal → русское название
_EXPORT_COLUMNS = [
    ("id", "№"),
    ("bin_iin", "БИН/ИИН"),
    ("region", "Область"),
    ("akimat", "Акимат"),
    ("direction", "Направление водства"),
    ("subsidy_type", "Наименование субсидирования"),
    ("district", "Район хозяйства"),
    ("normative", "Норматив"),
    ("amount", "Причитающая сумма"),
    ("score", "AI Балл"),
    ("category", "Категория"),
    ("review_required", "Рекомендуется доп. проверка"),
    ("created_at", "Дата оценки"),
    ("model_version", "Версия модели"),
]


@router.get("/export")
def export_applications(
    model_version: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
):
    """Экспорт оценённых заявок в Excel (с фильтрами)."""
    result = _repo().get_all(limit=10000, offset=0, model_version=model_version, category=category)

    if not result["items"]:
        raise HTTPException(400, "Нет данных для экспорта")

    rows = []
    for item in result["items"]:
        row = {}
        for internal, russian in _EXPORT_COLUMNS:
            val = item.get(internal)
            if internal == "bin_iin":
                # Сохраняем как строку с ведущими нулями
                raw = str(val) if val else ""
                # Убираем .0 если число было сохранено как float
                if raw.endswith(".0"):
                    raw = raw[:-2]
                row[russian] = raw
            elif internal == "review_required":
                row[russian] = "Да" if val else "Нет"
            elif internal == "category":
                cat_map = {"HIGH": "Высокий", "MEDIUM": "Средний", "LOW": "Низкий"}
                row[russian] = cat_map.get(str(val), str(val or ""))
            elif internal == "created_at":
                row[russian] = str(val)[:19] if val else ""
            else:
                row[russian] = val if val is not None else ""
        rows.append(row)

    df = pd.DataFrame(rows)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Результаты AgriScore")
        ws = writer.sheets["Результаты AgriScore"]

        # Найти столбец БИН/ИИН и отформатировать как текст
        bin_col_idx = None
        for idx, (_, russian) in enumerate(_EXPORT_COLUMNS, 1):
            if russian == "БИН/ИИН":
                bin_col_idx = idx
                break
        if bin_col_idx:
            col_letter = get_column_letter(bin_col_idx)
            for row_num in range(2, len(df) + 2):
                cell = ws[f"{col_letter}{row_num}"]
                # Принудительно записываем как строку
                cell.value = str(cell.value) if cell.value is not None else ""
                cell.number_format = "@"

    buf.seek(0)

    from urllib.parse import quote
    filename = "Результаты_AgriScore.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        },
    )
