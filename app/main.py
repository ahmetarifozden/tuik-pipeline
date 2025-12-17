from fastapi import FastAPI
from app.core.db import engine, Base
from app.api.routes import health
from app.models.dataset import Dataset 
from app.api.routes.datasets import router as datasets_router

def create_app() -> FastAPI:
    app = FastAPI(title="TUIK Data Pipeline API")
    app.include_router(health.router, tags=["health"])

    # MVP: tabloları otomatik oluştur (sonra Alembic’e geçeriz)
    Base.metadata.create_all(bind=engine)
    return app

app = create_app()
app.include_router(datasets_router)