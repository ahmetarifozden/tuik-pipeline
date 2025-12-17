from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.db import get_db
from app.models.dataset import Dataset
from app.schemas.dataset import DatasetOut

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
