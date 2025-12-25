import re
from pathlib import Path
from io import BytesIO

import yaml
import requests
from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.dataset import Dataset


CRAWL_YAML = Path("config/crawl.yaml")
DOWNLOADS_ROOT = Path("downloads")


def load_keywords_from_crawl_yaml(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Config bulunamadı: {path}")

    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    targets = cfg.get("targets", [])
    keywords = [t.get("query") for t in targets if t.get("type") == "keyword" and t.get("query")]
    # unique + sıra koru
    uniq = []
    seen = set()
    for kw in keywords:
        kw = str(kw).strip()
        if kw and kw not in seen:
            seen.add(kw)
            uniq.append(kw)
    return uniq


def safe_filename(text: str, max_len: int = 200) -> str:
    text = (text or "").strip()
    # Windows/Linux yasaklı karakterler
    text = re.sub(r"[\\/:*?\"<>|]+", "", text)
    text = re.sub(r"\s+", " ", text)
    text = text[:max_len].rstrip()
    return text or "untitled"


def safe_dirname(text: str, max_len: int = 80) -> str:
    # klasör adı için daha kısa ve sade
    text = (text or "").strip().lower()
    text = re.sub(r"[\\/:*?\"<>|]+", "", text)
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^0-9a-zA-ZğüşöçıİĞÜŞÖÇ_-]+", "", text)
    text = text[:max_len].strip("_")
    return text or "keyword"


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    i = 1
    while True:
        cand = path.with_name(f"{stem}_{i}{suffix}")
        if not cand.exists():
            return cand
        i += 1


def detect_extension(resp: requests.Response, fallback_url: str) -> str:
    ct = (resp.headers.get("Content-Type") or "").lower()

    if "pdf" in ct:
        return ".pdf"
    if "excel" in ct or "spreadsheet" in ct:
        return ".xlsx"
    if "csv" in ct:
        return ".csv"

    m = re.search(r"\.(xlsx|xls|pdf|csv)\b", (fallback_url or "").lower())
    if m:
        ext = m.group(1)
        return ".xlsx" if ext == "xls" else f".{ext}"

    return ".bin"


def fetch_rows_by_keyword(db: Session, q: str):
    q = q.strip()
    stmt = (
        select(Dataset.title, Dataset.download_url, Dataset.group_name)
        .where(
            or_(
                Dataset.group_name.ilike(f"%{q}%"),
                Dataset.title.ilike(f"%{q}%"),
            )
        )
        .order_by(Dataset.group_name, Dataset.title)
    )
    return db.execute(stmt).all()

def sniff_extension_from_bytes(data: bytes) -> str:
    if data.startswith(b"%PDF"):
        return ".pdf"
    if data.startswith(b"PK"):  # xlsx = zip
        return ".xlsx"
    # OLE2 / old xls signature
    if data.startswith(b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"):
        return ".xls"
    return ".bin"


def download_one(url: str, title: str, out_dir: Path) -> Path:
    resp = requests.get(url, timeout=90)
    resp.raise_for_status()

    data = resp.content
    ext = sniff_extension_from_bytes(data)
    fname = safe_filename(title) + ext
    path = unique_path(out_dir / fname)

    path.write_bytes(data)
    return path



def main():
    keywords = load_keywords_from_crawl_yaml(CRAWL_YAML)
    if not keywords:
        raise RuntimeError(f"{CRAWL_YAML} içinde type: keyword bulunamadı.")

    print(f"[INFO] crawl.yaml keyword sayısı: {len(keywords)} -> {keywords}")

    DOWNLOADS_ROOT.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        for kw in keywords:
            folder = DOWNLOADS_ROOT / safe_dirname(kw)
            folder.mkdir(parents=True, exist_ok=True)

            rows = fetch_rows_by_keyword(db, kw)
            print(f'\n=== KEYWORD: "{kw}" | found={len(rows)} | folder={folder} ===')

            ok = 0
            fail = 0

            for i, (title, download_url, group_name) in enumerate(rows, start=1):
                if not download_url:
                    continue

                try:
                    saved = download_one(download_url, title, folder)
                    ok += 1
                    print(f"{i:04d}) OK  -> {saved.name}")
                except Exception as e:
                    fail += 1
                    print(f"{i:04d}) ERR -> {title}")
                    print(f"      url: {download_url}")
                    print(f"      err: {e}")

            print(f'[DONE] "{kw}" indirilen={ok} hata={fail} klasör={folder}')

    finally:
        db.close()


if __name__ == "__main__":
    main()
