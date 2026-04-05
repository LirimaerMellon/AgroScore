"""Точка входа: запуск FastAPI-сервера через uvicorn."""

import uvicorn

from app.setup_dirs import init_directories


if __name__ == "__main__":
    init_directories()

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=["app"],
        reload_includes=["*.py"],
    )