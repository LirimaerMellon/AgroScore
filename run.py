import uvicorn

from app.setup_dirs import init_directories


if __name__ == "__main__":
    # 1. Инициализация окружения
    init_directories()

    # 2. Запуск FastAPI приложения
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )