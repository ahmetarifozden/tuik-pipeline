from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session
from urllib.parse import urljoin

from app.core.db import SessionLocal
from app.models.dataset import Dataset
from app.services.tuik.client import TuikClient
from urllib.parse import urlparse
from sqlalchemy import and_

from pathlib import Path
import re
import yaml
from urllib.parse import urlparse, parse_qs

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATEGORIES_YAML = PROJECT_ROOT / "config" / "categories.yaml"
BASE = "https://data.tuik.gov.tr"

def normalize_download_path(path: str) -> str:
    return urlparse(path).path


def load_ust_ids_from_yaml() -> list[int]:
    with open(CATEGORIES_YAML, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    urls = data.get("categories_pages", [])
    ust_ids = []
    for u in urls:
        parsed = urlparse(u)
        p = parse_qs(parsed.query).get("p", [None])[0]
        if not p:
            continue

        # p örn: "Cevre-ve-Enerji-103" -> sondaki sayıyı çek
        m = re.search(r"-(\d+)$", p)
        if not m:
            continue
        ust_ids.append(int(m.group(1)))

    # unique ama sıra korunsun
    uniq = []
    seen = set()
    for x in ust_ids:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def parse_page(html: str):
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
            "download_url": urljoin(BASE, raw_path),
        })

    keys = [(it["download_path"], it["title"]) for it in items]
    print("items:", len(items), "unique:", len(set(keys)))

    return items


def upsert_items(db: Session, ust_id: int, items: list[dict]):
    uniq = {}
    for it in items:
        key = (ust_id, it["download_path"], it["title"])
        uniq[key] = it  # aynı key gelirse sonuncusu kalsın
    items = list(uniq.values())
    new_count = 0

    for it in items:
        existing = db.execute(
            select(Dataset)
            .where(Dataset.ust_id == ust_id)
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
                ust_id=ust_id,
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



def main():
    client = TuikClient()
    ust_ids = load_ust_ids_from_yaml()
    print(f"[START] categories.yaml içinden ust_id sayısı: {len(ust_ids)} -> {ust_ids}")

    grand_total = 0
    grand_new = 0

    with SessionLocal() as db:
        for ust_id in ust_ids:
            html = client.get_istatistiksel_tablolar(
                ust_id=ust_id, page=1, count=50, dil_id=1, arsiv=False
            )

            items = parse_page(html)
            new_count = upsert_items(db, ust_id, items)

            print(f"[UST {ust_id}] total_items={len(items)} new_inserted={new_count}")

            grand_total += len(items)
            grand_new += new_count

    print(f"[DONE] grand_total_items={grand_total} grand_new_inserted={grand_new}")




if __name__ == "__main__":
    main()
