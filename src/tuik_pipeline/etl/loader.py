import pandas as pd
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.tuik_pipeline.core.logging import get_logger
from src.tuik_pipeline.core.database import SessionLocal
from src.tuik_pipeline.models.dataset import Dataset
from src.tuik_pipeline.models.observation import Observation

logger = get_logger(__name__)

def iter_csv_files(root: Path):
    for p in root.rglob("*.csv"):
        if p.is_file():
            yield p

def guess_dataset_id(db: Session, source_file: str) -> int | None:
    """
    Fallback method to match file to a dataset ID if columns are missing.
    Matches using Group Name (folder) and Title (filename).
    """
    p = Path(source_file)
    title = p.stem.replace("_", " ").strip().lower()
    group_name = p.parent.name.replace("_", " ").strip().lower()

    stmt = (
        select(Dataset.id)
        .where(Dataset.group_name.ilike(f"%{group_name}%"))
        .where(Dataset.title.ilike(f"%{title[:40]}%"))
        .limit(1)
    )
    row = db.execute(stmt).first()
    return row[0] if row else None

def run_loader_pipeline(root_path_str: str, limit: int = 0):
    root = Path(root_path_str)
    files = list(iter_csv_files(root))
    
    if limit > 0:
        files = files[:limit]

    logger.info(f"Loading files from root={root}, count={len(files)}")

    db = SessionLocal()
    try:
        ok_count = 0
        fail_count = 0
        total_inserted = 0

        for i, csv_path in enumerate(files, start=1):
            try:
                df = pd.read_csv(csv_path)

                if "year" not in df.columns:
                    raise ValueError("CSV missing 'year' column")

                # Resolve dataset_id
                source_file = df["source_file"].iloc[0] if "source_file" in df.columns else str(csv_path)
                
                if "dataset_id" in df.columns and pd.notnull(df["dataset_id"].iloc[0]):
                    dataset_id = int(df["dataset_id"].iloc[0])
                else:
                    dataset_id = guess_dataset_id(db, source_file)

                if not dataset_id:
                    raise ValueError(f"Could not resolve dataset_id for: {source_file}")

                # Clean and Validations
                df = df.where(pd.notnull(df), None)
                
                # Check year format
                df["year"] = df["year"].astype(str).str.strip()
                df = df[df["year"].str.match(r"^(19|20)\d{2}$", na=False)]
                df["year"] = df["year"].astype(int)

                if "threshold" in df.columns:
                    df["threshold"] = df["threshold"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
                
                df["value"] = pd.to_numeric(df["value"], errors="coerce")

                rows_to_insert = []
                for _, r in df.iterrows():
                    rows_to_insert.append(
                        Observation(
                            dataset_id=dataset_id,
                            year=int(r["year"]), # Already vetted above
                            threshold=str(r.get("threshold")) if r.get("threshold") else None,
                            metric=str(r.get("metric")) if r.get("metric") else "unknown",
                            education=str(r.get("education")) if r.get("education") else None,
                            value=r.get("value"),
                            source_file=str(csv_path),
                        )
                    )

                if rows_to_insert:
                    db.add_all(rows_to_insert)
                    db.commit()
                    total_inserted += len(rows_to_insert)

                ok_count += 1
                logger.info(f"[{i:04d}] OK -> {csv_path.name} (rows={len(rows_to_insert)})")

            except Exception as e:
                db.rollback()
                fail_count += 1
                logger.error(f"Failed to load {csv_path.name}: {e}")

        logger.info(f"Loader Summary: OK={ok_count} FAIL={fail_count} INSERTED={total_inserted}")

    finally:
        db.close()
