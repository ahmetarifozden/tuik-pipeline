from fastapi import FastAPI
from src.tuik_pipeline.core.database import engine, Base
from src.tuik_pipeline.api.routes import health, datasets
from src.tuik_pipeline.core.logging import setup_logging

def create_app() -> FastAPI:
    setup_logging()
    
    app = FastAPI(title="TUIK Data Pipeline API")
    
    app.include_router(health.router, tags=["health"])
    app.include_router(datasets.router)

    # Initialize DB (MVP style)
    # Ideally should be done via migration scripts
    Base.metadata.create_all(bind=engine)
    
    return app

app = create_app()

@app.get("/")
def root():
    return {"status": "ok", "docs": "/docs"}
