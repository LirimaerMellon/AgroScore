from fastapi import FastAPI
from app.models import Base
from app.db import engine
from app.api.user_router import router

app = FastAPI()

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

app.include_router(router)