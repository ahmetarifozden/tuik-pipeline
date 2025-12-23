import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from sqlalchemy import select, or_
from app.models.dataset import Dataset

from app.core.db import SessionLocal
from app.models.category import Category
from scripts.crawl_all_tables import crawl_one  # crawl_one fonksiyonun burada var diye varsayıyorum

def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)



def resolve_ust_ids(db: Session, targets: list[dict]) -> list[int]:
    ust_ids = set()

    for t in targets:
        if t["type"] == "ust_id":
            ust_ids.add(int(t["id"]))
            continue

        if t["type"] == "keyword":
            q = t["query"].strip()

            rows = db.execute(
                select(Dataset.ust_id)
                .where(
                    or_(
                        Dataset.group_name.ilike(f"%{q}%"),
                        Dataset.title.ilike(f"%{q}%"),
                    )
                )
                .distinct()
            ).all()

            found = [r[0] for r in rows]
            print(f'[MATCH] keyword="{q}" -> ust_ids={found}')

            for uid in found:
                ust_ids.add(int(uid))

            continue

        raise ValueError(f"Unknown target type: {t['type']}")

    return sorted(ust_ids)


def get_alt_ids(db: Session, ust_id: int) -> list[int]:
    rows = db.execute(
        select(Category.id).where(Category.parent_id == ust_id)
    ).all()
    return [int(r[0]) for r in rows]

def main():
    cfg = load_config("config/crawl.yaml")
    crawl_cfg = cfg.get("crawl", {})
    count = int(crawl_cfg.get("count", 50))
    archived = bool(crawl_cfg.get("archived", False))
    stop_on_error = bool(crawl_cfg.get("stop_on_error", False))

    targets = cfg.get("targets", [])
    if not targets:
        raise RuntimeError("No targets in config/crawl.yaml")

    db = SessionLocal()
    try:
        ust_ids = resolve_ust_ids(db, targets)
        print(f"[CONFIG] resolved ust_ids={ust_ids}")

        for ust_id in ust_ids:
            alt_ids = get_alt_ids(db, ust_id)
            print(f"[UST] ust_id={ust_id} alt_count={len(alt_ids)} sample={alt_ids[:10]}")

            for alt_id in alt_ids:
                try:
                    crawl_one(ust_id=ust_id, alt_id=alt_id, count=count, arsiv=archived)
                except Exception as e:
                    print(f"[ERR] ust_id={ust_id} alt_id={alt_id}: {e}")
                    if stop_on_error:
                        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
