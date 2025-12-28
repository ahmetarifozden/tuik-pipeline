import re
import csv
import yaml
import requests
import sys
from pathlib import Path
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from typing import Optional

from src.tuik_pipeline.core.logging import get_logger
from src.tuik_pipeline.core.database import SessionLocal
from src.tuik_pipeline.models.dataset import Dataset

logger = get_logger(__name__)

def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def fetch_datasets_by_keyword(db: Session, q: str):
    q = q.strip()
    stmt = (
        select(Dataset.id, Dataset.group_name, Dataset.title, Dataset.download_url)
        .where(
            or_(
                Dataset.group_name.ilike(f"%{q}%"),
                Dataset.title.ilike(f"%{q}%"),
            )
        )
        .order_by(Dataset.group_name, Dataset.title)
    )
    return db.execute(stmt).all()

def safe_dirname(text: str, max_len: int = 80) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[\\/:*?\"<>|]+", "", text)
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^0-9a-zA-ZğüşöçıİĞÜŞÖÇ_-]+", "", text)
    text = text[:max_len].strip("_")
    return text or "keyword"

def normalize_title(title: str) -> str:
    s = (title or "").strip()
    s = s.lstrip("\ufeff").strip()
    pattern = r"^\s*istatistiksel\s+tablolar\s*([\-–—:|»]\s*)?"
    s = re.sub(pattern, "", s, flags=re.IGNORECASE).strip()
    return s or (title or "untitled").strip()

def safe_filename(text: str, max_len: int = 200) -> str:
    text = (text or "").strip()
    text = re.sub(r"[\\/:*?\"<>|]+", "", text)
    text = re.sub(r"\s+", " ", text)
    text = text[:max_len].rstrip()
    return text or "untitled"

def get_unique_path(path: Path) -> Path:
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

def sniff_extension_from_bytes(data: bytes) -> str:
    if data.startswith(b"%PDF"):
        return ".pdf"
    if data.startswith(b"PK"):  # xlsx/zip
        return ".xlsx"
    if data.startswith(b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"):  # OLE2 xls/doc
        return ".xls"
    return ".bin"

def download_file(url: str, title: str, out_dir: Path) -> Path:
    resp = requests.get(url, timeout=90)
    resp.raise_for_status()
    data = resp.content
    ext = sniff_extension_from_bytes(data)
    clean_title = normalize_title(title)
    fname = safe_filename(clean_title) + ext
    path = get_unique_path(out_dir / fname)
    path.write_bytes(data)
    return path

def run_downloader_pipeline(
    keyword_arg: Optional[str] = None, 
    config_path: str = "config/crawl.yaml", 
    skip_prompt: bool = False
):
    if keyword_arg:
        keywords = [keyword_arg]
    else:
        cfg = load_config(config_path)
        targets = cfg.get("targets", [])
        keywords = [t["query"] for t in targets if t.get("type") == "keyword" and t.get("query")]

    db = SessionLocal()
    try:
        all_results = {}
        total_rows = 0

        for kw in keywords:
            rows = fetch_datasets_by_keyword(db, kw)
            all_results[kw] = rows
            total_rows += len(rows)

            logger.info(f'KEYWORD: "{kw}" | found={len(rows)}')
            for i, (ds_id, grp, title, url) in enumerate(rows, start=1):
                print(f"  {i:02d}) {grp} | {title}")

        if total_rows == 0:
            logger.info("No records found to download.")
            return

        if not skip_prompt:
            ans = input("\nDo you want to proceed with downloading? (y/n): ").strip().lower()
            if ans not in ("y", "yes", "evet", "e"):
                logger.info("Download cancelled.")
                return # Simply return, caller script checks for manifest file creation

        downloads_root = Path("downloads")
        grand_ok = 0
        grand_fail = 0

        for kw in keywords:
            rows = all_results.get(kw, [])
            if not rows: continue

            kw_folder = downloads_root / safe_dirname(kw)
            kw_folder.mkdir(parents=True, exist_ok=True)
            
            manifest_path = kw_folder / "manifest.csv"
            
            with open(manifest_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["dataset_id","keyword","group_name","title","download_url","saved_path"],
                )
                writer.writeheader()
                kw_ok = 0
                kw_fail = 0

                for i, (ds_id, grp, title, url) in enumerate(rows, start=1):
                    if not url: continue
                    grp_folder = kw_folder / safe_dirname(grp or "unknown_group")
                    grp_folder.mkdir(parents=True, exist_ok=True)
                    try:
                        saved = download_file(url, title, grp_folder)
                        clean_title = normalize_title(title)
                        writer.writerow({
                            "dataset_id": ds_id,
                            "keyword": kw,
                            "group_name": grp,
                            "title": clean_title,
                            "download_url": url,
                            "saved_path": str(saved),
                        })
                        kw_ok += 1
                        logger.info(f"[{kw}] OK -> {saved.name}")
                    except Exception as e:
                        kw_fail += 1
                        logger.error(f"[{kw}] ERR -> {title} | {e}")
                
                grand_ok += kw_ok
                grand_fail += kw_fail
        
        logger.info(f"Download Summary: OK={grand_ok} FAIL={grand_fail}")
        
    finally:
        db.close()
