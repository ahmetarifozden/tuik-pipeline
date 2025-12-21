from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.db import get_db
from app.models.dataset import Dataset
from app.schemas.dataset import DatasetOut

import requests
import pandas as pd
from io import BytesIO


router = APIRouter(prefix="/datasets", tags=["datasets"])

@router.get("", response_model=list[DatasetOut])
def list_datasets(
    ust_id: int | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(Dataset)
    if ust_id is not None:
        stmt = stmt.where(Dataset.ust_id == ust_id)

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

def load_tuik_excel(download_url: str) -> pd.DataFrame:
    r = requests.get(download_url, timeout=60)
    r.raise_for_status()
    return pd.read_excel(BytesIO(r.content), skiprows=3)

@router.get("/{dataset_id}/table")
def get_dataset_table(
    dataset_id: int,
    db: Session = Depends(get_db),
):
    ds = db.get(Dataset, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")

    url = ds.download_url  # SQLAlchemy modelinden geliyor

    df = load_tuik_excel(url)

    df = df.dropna(how="all").fillna("")

    return {
        "dataset_id": dataset_id,
        "columns": list(df.columns),
        "rows": df.to_dict(orient="records"),
    }
