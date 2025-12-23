import yaml
from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.dataset import Dataset  # __tablename__ = "datastes" olan model

def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def fetch_rows_by_keyword(db: Session, q: str):
    q = q.strip()
    stmt = (
        select(Dataset.group_name, Dataset.title, Dataset.download_url)
        .where(
            or_(
                Dataset.group_name.ilike(f"%{q}%"),
                Dataset.title.ilike(f"%{q}%"),
            )
        )
        .order_by(Dataset.group_name, Dataset.title)
    )
    return db.execute(stmt).all()

def main():
    cfg = load_config("config/crawl.yaml")
    targets = cfg.get("targets", [])
    if not targets:
        raise RuntimeError("No targets in config/crawl.yaml")

    # sadece keyword'leri al
    keywords = [t["query"] for t in targets if t.get("type") == "keyword"]
    if not keywords:
        raise RuntimeError("Config içinde type: keyword yok")

    db = SessionLocal()
    try:
        for kw in keywords:
            rows = fetch_rows_by_keyword(db, kw)
            print(f'\n=== KEYWORD: "{kw}" | found={len(rows)} ===')

            for i, (group_name, title, download_url) in enumerate(rows, start=1):
                print(f"{i:04d})")
                print(f"  group_name : {group_name}")
                print(f"  title      : {title}")
                print(f"  download   : {download_url}")
                print("-" * 60)
    finally:
        db.close()

if __name__ == "__main__":
    main()
