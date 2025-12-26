import argparse
from pathlib import Path
import pandas as pd
import re
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.dataset import Dataset
from app.models.observation import Observation


def iter_csvs(root: Path):
    for p in root.rglob("*.csv"):
        if p.is_file():
            yield p


def guess_dataset_id(db: Session, source_file: str) -> int | None:
    """
    Şimdilik basit eşleştirme:
    - source_file path içindeki group_name ile
    - dosya adındaki title benzerliğiyle
    daha sağlam hale getireceğiz, ama ilk yükleme için bu yeterli olabilir.

    EN DOĞRU yöntem: normalize script'ine dataset_id eklemek (sonra iyileştiririz).
    """
    p = Path(source_file)
    title = p.stem.replace("_", " ").strip().lower()
    group_name = p.parent.name.replace("_", " ").strip().lower()

    stmt = (
        select(Dataset.id)
        .where(Dataset.group_name.ilike(f"%{group_name}%"))
        .where(Dataset.title.ilike(f"%{title[:40]}%"))  # çok uzun olmasın
        .limit(1)
    )
    row = db.execute(stmt).first()
    return row[0] if row else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", help="normalized klasörü (örn: normalized/yoksulluk veya normalized)")
    parser.add_argument("--limit", type=int, default=0, help="test için ilk N csv (0=hepsi)")
    args = parser.parse_args()

    root = Path(args.root)
    files = list(iter_csvs(root))
    if args.limit and args.limit > 0:
        files = files[:args.limit]

    print(f"[INFO] root={root} csv_count={len(files)}")

    db = SessionLocal()
    try:
        ok = 0
        fail = 0
        inserted = 0

        for i, csv_path in enumerate(files, start=1):
            try:
                df = pd.read_csv(csv_path)
                df = pd.read_csv(csv_path)

                if "year" not in df.columns:
                    raise RuntimeError("CSV'de year kolonu yok")
                # beklenen kolonlar: year, threshold, metric_education, value, metric, education, source_file
                # bazı dosyalarda year/threshold isimleri farklıysa burada map yaparız.

                # dataset_id bul
                source_file = df["source_file"].iloc[0] if "source_file" in df.columns else str(csv_path)
                dataset_id = guess_dataset_id(db, source_file)
                if not dataset_id:
                    raise RuntimeError(f"dataset_id bulunamadı (eşleşmedi): {source_file}")

                # NaN -> None
                df = df.where(pd.notnull(df), None)
                df["year"] = df["year"].astype(str).str.strip()
                df = df[df["year"].str.match(r"^(19|20)\d{2}$", na=False)]
                df["year"] = df["year"].astype(int)
                df["threshold"] = df["threshold"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
                
                if "threshold" in df.columns:
                    df["threshold"] = df["threshold"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
                
                df["value"] = pd.to_numeric(df["value"], errors="coerce")

                rows = []
                for _, r in df.iterrows():
                    rows.append(
                        Observation(
                            dataset_id=dataset_id,
                            year=int(r["year"]) if r.get("year") is not None else None,
                            threshold=str(r.get("threshold")) if r.get("threshold") is not None else None,
                            metric=str(r.get("metric")) if r.get("metric") is not None else "unknown",
                            education=str(r.get("education")) if r.get("education") is not None else None,
                            value=r.get("value"),
                            source_file=str(csv_path),
                        )
                    )

                db.add_all(rows)
                db.commit()

                ok += 1
                inserted += len(rows)
                print(f"[{i:04d}] OK  rows={len(rows)} dataset_id={dataset_id} -> {csv_path}")

            except Exception as e:
                db.rollback()
                fail += 1
                print(f"[{i:04d}] ERR -> {csv_path}")
                print(f"       err: {e}")

        print(f"[DONE] ok={ok} fail={fail} inserted={inserted}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
