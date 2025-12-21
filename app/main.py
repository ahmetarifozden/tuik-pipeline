from fastapi import FastAPI
from app.core.db import engine, Base
from app.api.routes import health
from app.models.dataset import Dataset 
from app.api.routes.datasets import router as datasets_router
import requests
import pandas as pd
from io import BytesIO


def create_app() -> FastAPI:
    app = FastAPI(title="TUIK Data Pipeline API")
    app.include_router(health.router, tags=["health"])

    # MVP: tabloları otomatik oluştur (sonra Alembic’e geçeriz)
    Base.metadata.create_all(bind=engine)
    return app

app = create_app()
app.include_router(datasets_router)

def load_tuik_excel(download_url: str) -> pd.DataFrame:
    r = requests.get(download_url, timeout=60)
    r.raise_for_status()
    return pd.read_excel(BytesIO(r.content), skiprows=3)


@app.get("/")
def root():
    return {"status": "ok", "docs": "/docs"}
