from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
import requests
import pandas as pd
from io import BytesIO

from src.tuik_pipeline.core.database import get_db
from src.tuik_pipeline.models.dataset import Dataset
from src.tuik_pipeline.schemas.dataset import DatasetOut
from src.tuik_pipeline.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/datasets", tags=["datasets"])

@router.get("", response_model=list[DatasetOut])
def list_datasets(
    parent_id: int | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(Dataset)
    if parent_id is not None:
        stmt = stmt.where(Dataset.ust_id == parent_id)

    return db.scalars(stmt).all()

@router.get("/{dataset_id}", response_model=DatasetOut)
def get_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
):
    ds = db.get(Dataset, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return ds

def load_excel_preview(download_url: str) -> pd.DataFrame:
    try:
        r = requests.get(download_url, timeout=60)
        r.raise_for_status()
        return pd.read_excel(BytesIO(r.content), skiprows=3)
    except Exception as e:
        logger.error(f"Failed to load excel for preview: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch or parse Excel file from remote.")

@router.get("/{dataset_id}/table")
def get_dataset_table(
    dataset_id: int,
    db: Session = Depends(get_db),
):
    ds = db.get(Dataset, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")

    url = ds.download_url
    df = load_excel_preview(url)
    df = df.dropna(how="all").fillna("")

    return {
        "dataset_id": dataset_id,
        "columns": list(df.columns),
        "rows": df.to_dict(orient="records"),
    }
