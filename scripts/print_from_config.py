import argparse
import re
from pathlib import Path
import csv

import yaml
import requests
from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.dataset import Dataset


DEFAULT_CONFIG = "config/crawl.yaml"
DOWNLOADS_ROOT = Path("downloads")


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def fetch_rows_by_keyword(db: Session, q: str):
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
    """
    Başta geçen 'İstatistiksel Tablolar' ifadesini (çeşitli tire/boşluk varyasyonlarıyla)
    kaldırır ve temiz bir title döndürür.
    """
    s = (title or "").strip()

    # Başta BOM/garip whitespace olabiliyor
    s = s.lstrip("\ufeff").strip()

    # TÜİK başlık prefix'i: İstatistiksel Tablolar  / İSTATİSTİKSEL TABLOLAR
    # Ardından gelebilecek: "-", "–", "—", ":", "|", "»" vb. ayraçları da temizle
    pattern = r"^\s*istatistiksel\s+tablolar\s*([\-–—:|»]\s*)?"
    s = re.sub(pattern, "", s, flags=re.IGNORECASE).strip()

    # Eğer tamamen boş kaldıysa fallback
    return s or (title or "untitled").strip()


def safe_filename(text: str, max_len: int = 200) -> str:
    text = (text or "").strip()
    text = re.sub(r"[\\/:*?\"<>|]+", "", text)
    text = re.sub(r"\s+", " ", text)
    text = text[:max_len].rstrip()
    return text or "untitled"


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


def sniff_extension_from_bytes(data: bytes) -> str:
    if data.startswith(b"%PDF"):
        return ".pdf"
    if data.startswith(b"PK"):  # xlsx/zip
        return ".xlsx"
    if data.startswith(b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"):  # OLE2 xls/doc
        return ".xls"
    return ".bin"


def download_one(url: str, title: str, out_dir: Path) -> Path:
    resp = requests.get(url, timeout=90)
    resp.raise_for_status()
    data = resp.content

    ext = sniff_extension_from_bytes(data)

    clean_title = normalize_title(title)   # <-- ekledik
    fname = safe_filename(clean_title) + ext

    path = unique_path(out_dir / fname)
    path.write_bytes(data)
    return path


def ask_yes_no(prompt: str) -> bool:
    ans = input(prompt).strip().lower()
    return ans in ("e", "evet", "y", "yes")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "keyword",
        nargs="?",
        help="Tek keyword ile arama (örn: ciro). Vermezsen config'ten okur.",
    )
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument(
        "--no-download-prompt",
        action="store_true",
        help="Sonda indirme sorusu sorma.",
    )
    args = parser.parse_args()

    # keyword listesi belirle
    if args.keyword:
        keywords = [args.keyword]
        config_path = None
    else:
        config_path = args.config
        cfg = load_config(config_path)
        targets = cfg.get("targets", [])
        if not targets:
            raise RuntimeError(f"No targets in {config_path}")

        keywords = [t["query"] for t in targets if t.get("type") == "keyword" and t.get("query")]
        if not keywords:
            raise RuntimeError("Config içinde type: keyword yok")

    db = SessionLocal()
    try:
        all_results: dict[str, list[tuple[str, str, str]]] = {}  # kw -> rows
        total = 0

        if config_path:
            print(f"[INFO] Config: {config_path}")

        for kw in keywords:
            rows = fetch_rows_by_keyword(db, kw)
            all_results[kw] = rows
            total += len(rows)

            print(f'\n=== KEYWORD: "{kw}" | found={len(rows)} ===')
            for i, (dataset_id, group_name, title, download_url) in enumerate(rows, start=1):
                print(f"{i:04d})")
                print(f"  group_name : {group_name}")
                print(f"  title      : {title}")
                print(f"  download   : {download_url}")
                print("-" * 60)

        print(f"\n[SUMMARY] keyword_count={len(keywords)} total_rows={total}")

        if args.no_download_prompt:
            return

        if total == 0:
            print("[INFO] İndirilecek kayıt yok.")
            return

        if not ask_yes_no("\nİndirmek ister misiniz? (E/H): "):
            print("[INFO] İndirme iptal edildi.")
            return

        # İndirme
        DOWNLOADS_ROOT.mkdir(parents=True, exist_ok=True)
        print("\n[DOWNLOAD] Başlıyor...")

        grand_ok = 0
        grand_fail = 0

        for kw in keywords:
            rows = all_results.get(kw, [])
            if not rows:
                continue

            kw_folder = DOWNLOADS_ROOT / safe_dirname(kw)
            kw_folder.mkdir(parents=True, exist_ok=True)
            manifest_path = kw_folder / "manifest.csv"
            manifest_f = open(manifest_path, "w", newline="", encoding="utf-8")
            writer = csv.DictWriter(
                manifest_f,
                fieldnames=["dataset_id","keyword","group_name","title","download_url","saved_path"],
            )
            writer.writeheader()
            ok = 0
            fail = 0

            for i, (dataset_id, group_name, title, url) in enumerate(rows, start=1):
                if not url:
                    continue

                # keyword klasörü altında group klasörü
                group_folder = kw_folder / safe_dirname(group_name or "unknown_group")
                group_folder.mkdir(parents=True, exist_ok=True)

                try:
                    saved = download_one(url, title, group_folder)
                    writer.writerow({
                        "dataset_id": dataset_id,
                        "keyword": kw,
                        "group_name": group_name,
                        "title": title,
                        "download_url": url,
                        "saved_path": str(saved),
                    })
                    ok += 1
                    print(f'[{kw}] {i:04d}) OK  -> {group_folder.name}/{saved.name}')
                except Exception as e:
                    fail += 1
                    print(f'[{kw}] {i:04d}) ERR -> {title}')
                    print(f"      group: {group_name}")
                    print(f"      url  : {url}")
                    print(f"      err  : {e}")

            grand_ok += ok
            grand_fail += fail
            print(f'[DONE] "{kw}" indirilen={ok} hata={fail} klasör={kw_folder}')
        
        manifest_f.close()
        print(f"[MANIFEST] yazıldı -> {manifest_path}")

        print(f"\n[DOWNLOAD SUMMARY] ok={grand_ok} fail={grand_fail} root=./downloads")

    finally:
        db.close()


if __name__ == "__main__":
    main()
