from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session
from urllib.parse import urljoin

from app.core.db import SessionLocal
from app.models.dataset import Dataset
from app.services.tuik.client import TuikClient

BASE = "https://data.tuik.gov.tr"

def parse_page(html: str):
    soup = BeautifulSoup(html, "lxml")
    table = soup.select_one("table#istatistikselTable")
    if not table:
        return []

    current_group = None
    items = []

    for tr in table.select("tbody tr"):
        cls = " ".join(tr.get("class", []))

        # group row
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
        download_path = a["href"] if a else None
        if not title or not download_path:
            continue

        items.append({
            "group": current_group,
            "title": title,
            "date": date_text,
            "download_path": download_path,
            "download_url": urljoin(BASE, download_path),
        })

    return items

def upsert_items(db: Session, ust_id: int, items: list[dict]):
    new_count = 0
    for it in items:
        existing = db.execute(
            select(Dataset).where(Dataset.download_path == it["download_path"])
        ).scalar_one_or_none()

        if existing:
            # update (title/date/group değişmiş olabilir)
            existing.ust_id = ust_id
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
    ust_id = 109
    client = TuikClient()

    html = client.get_istatistiksel_tablolar(
        ust_id=ust_id, page=1, count=50, dil_id=1, arsiv=False
    )

    items = parse_page(html)

    with SessionLocal() as db:
        new_count = upsert_items(db, ust_id, items)

    print(f"DONE. total_items={len(items)} new_inserted={new_count}")


if __name__ == "__main__":
    main()
