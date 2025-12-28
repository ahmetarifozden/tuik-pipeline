import sys
import requests
import yaml
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.tuik_pipeline.core.logging import get_logger
from src.tuik_pipeline.services.tuik_client import TuikClient
from src.tuik_pipeline.models.dataset import Dataset
from src.tuik_pipeline.core.config import settings
from src.tuik_pipeline.core.database import SessionLocal

logger = get_logger(__name__)

BASE_URL = settings.tuik_base_url

def fetch_html(url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text

def extract_categories_from_html(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()

        if href.startswith("javascript:"):
            continue

        full_url = urljoin(BASE_URL, href)

        # Only category pages
        if "/Kategori/GetKategori" not in full_url:
            continue

        if full_url == BASE_URL:
            continue

        if full_url in seen:
            continue

        seen.add(full_url)
        urls.append(full_url)

    return urls

def update_categories_yaml(output_path: Path) -> int:
    try:
        html = fetch_html(BASE_URL)
    except Exception as e:
        logger.error(f"Failed to fetch base page: {e}")
        return 1

    cats = extract_categories_from_html(html)

    if not cats:
        logger.warning("No categories found. Site DOM structure might have changed.")
        return 2

    data = {
        "categories_pages": cats
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            data,
            f,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )

    logger.info(f"{len(cats)} categories written to -> {output_path}")
    return 0

# --- Dataset Seeding Logic ---

def normalize_download_path(path: str) -> str:
    return urlparse(path).path

def load_parent_ids_from_yaml(yaml_path: Path) -> list[int]:
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    urls = data.get("categories_pages", [])
    parent_ids = []
    for u in urls:
        parsed = urlparse(u)
        p = parse_qs(parsed.query).get("p", [None])[0]
        if not p:
            continue

        # e.g.: "Cevre-ve-Enerji-103" -> capture last digits
        m = re.search(r"-(\d+)$", p)
        if not m:
            continue
        parent_ids.append(int(m.group(1)))

    # unique while preserving order
    uniq = []
    seen = set()
    for x in parent_ids:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq

def parse_dataset_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    table = soup.select_one("table#istatistikselTable")
    if not table:
        return []

    current_group = None
    items = []

    for tr in table.select("tbody tr"):
        cls = " ".join(tr.get("class", []))

        if "dtrg-group" in cls:
            tds = tr.find_all("td")
            group_text = " ".join(td.get_text(" ", strip=True) for td in tds).strip()
            if group_text:
                current_group = group_text
            continue

        tds = tr.find_all("td")
        if len(tds) < 3:
            continue

        title = tds[0].get_text(" ", strip=True)
        date_text = tds[1].get_text(" ", strip=True)

        a = tds[2].find("a", href=True)
        raw_path = a["href"] if a else None
        if not raw_path:
            continue

        download_path = normalize_download_path(raw_path)

        items.append({
            "group": current_group,
            "title": title,
            "date": date_text,
            "download_path": download_path,
            "download_url": urljoin(BASE_URL, raw_path),
        })

    return items

def upsert_datasets(db: Session, parent_id: int, items: list[dict]) -> int:
    uniq = {}
    for it in items:
        key = (parent_id, it["download_path"], it["title"])
        uniq[key] = it
    items = list(uniq.values())
    new_count = 0

    for it in items:
        # Check existing using ORM
        existing = db.execute(
            select(Dataset)
            .where(Dataset.ust_id == parent_id)
            .where(Dataset.download_path == it["download_path"])
            .where(Dataset.title == it["title"])
        ).scalar_one_or_none()

        if existing:
            existing.group_name = it["group"]
            existing.title = it["title"]
            existing.publish_date_raw = it["date"]
            existing.download_url = it["download_url"]
        else:
            db.add(Dataset(
                ust_id=parent_id,
                group_name=it["group"],
                title=it["title"],
                publish_date_raw=it["date"],
                download_path=it["download_path"],
                download_url=it["download_url"],
                is_archived=False,
            ))
            new_count += 1

    db.commit()
    return new_count

def seed_datasets(yaml_path: Path):
    client = TuikClient()
    parent_ids = load_parent_ids_from_yaml(yaml_path)
    logger.info(f"Loaded {len(parent_ids)} parent IDs from {yaml_path}")

    grand_total = 0
    grand_new = 0

    with SessionLocal() as db:
        for pid in parent_ids:
            try:
                html = client.get_statistical_tables(
                    parent_id=pid, page=1, count=50, lang_id=1, archive=False
                )
                items = parse_dataset_page(html)
                new_count = upsert_datasets(db, pid, items)
                
                logger.debug(f"[Parent {pid}] total_items={len(items)} new_inserted={new_count}")

                grand_total += len(items)
                grand_new += new_count
            except Exception as e:
                logger.error(f"Error seeding for parent {pid}: {e}")

    logger.info(f"Done. grand_total_items={grand_total} grand_new_inserted={grand_new}")
