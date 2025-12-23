# scripts/crawl_all_tables.py
from __future__ import annotations

from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session
from urllib.parse import urljoin, urlparse

from app.core.db import SessionLocal
from app.models.dataset import Dataset
from app.services.tuik.client import TuikClient
import re
import requests
from bs4 import BeautifulSoup
BASE = "https://data.tuik.gov.tr"


def normalize_download_path(path: str) -> str:
    return urlparse(path).path


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

    return items


def upsert_items(db: Session, ust_id: int, items: list[dict]) -> int:
    # Sayfa içi dedup
    uniq = {}
    for it in items:
        key = (ust_id, it["download_path"], it["title"])
        uniq[key] = it
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


def _extract_alt_ids_from_json(obj) -> set[int]:
    """
    GetVeriSayilari JSON'u her ortamda aynı şemada olmayabilir.
    O yüzden JSON içinde dolaşıp alt kategori id'lerine benzeyen integer'ları topluyoruz.
    (Aşırı agresif olmasın diye: 1..2_000_000 arası int'ler)
    """
    alt_ids: set[int] = set()

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                # tipik anahtarlar
                if isinstance(v, int) and ("alt" in k.lower() and "id" in k.lower()):
                    if 1 <= v <= 2_000_000:
                        alt_ids.add(v)
                walk(v)
        elif isinstance(x, list):
            for i in x:
                walk(i)

    walk(obj)
    return alt_ids




def get_alt_ids(client, ust_id: int) -> list[int]:
    # Örn: Nufus-ve-Demografi-109
    # Bazı konular için slug farklı olabilir, o yüzden brute regex fallback de ekliyoruz.
    # Senin ekran görüntüsünde tam olarak bu var:
    url = f"https://data.tuik.gov.tr/Kategori/GetKategori?p=Nufus-ve-Demografi-{ust_id}"
    html = client.session.get(url, timeout=60).text

    # 1) BeautifulSoup ile checkbox/radio value topla (en temiz)
    soup = BeautifulSoup(html, "lxml")
    ids = set()

    for inp in soup.select("input"):
        v = inp.get("value")
        if v and v.isdigit():
            n = int(v)
            # alt id'ler genelde büyük olur (ör: 1047)
            if 1 <= n <= 2_000_000:
                ids.add(n)

    # 2) Bulamazsak regex fallback (HTML içinde id geçebilir)
    if not ids:
        for m in re.findall(r"\b(\d{2,7})\b", html):
            n = int(m)
            if 1 <= n <= 2_000_000:
                ids.add(n)

    # çok fazla “çöp id” çıkarsa burada filtreyi daraltırız
    return sorted(ids)



def crawl_one(ust_id: int, alt_id: int, slug: str, count: int = 50, arsiv: bool = False):
    client = TuikClient()

    # cookie/session prime
    referer = client.prime_category_session(ust_id=ust_id, slug=slug)

    print(f"[FETCH] ust_id={ust_id} alt_id={alt_id}", flush=True)

    html = client.get_istatistiksel_tablolar(
        ust_id=ust_id,
        page=1,          # sayfa parametresi dursa da tek sefer yeterli
        count=count,
        dil_id=1,
        arsiv=arsiv,
        alt_idler=[alt_id],
        referer=referer,
    )

    items = parse_page(html)
    print(f"[PARSE] items={len(items)}", flush=True)

    with SessionLocal() as db:
        new_count = upsert_items(db, ust_id, items)

    print(f"[DONE] ust_id={ust_id} alt_id={alt_id} total={len(items)} new_inserted={new_count}", flush=True)






def crawl_all(ust_ids: list[int], count: int = 50, arsiv: bool = False):
    client = TuikClient()

    for ust_id in ust_ids:
        alt_ids = get_alt_ids(client, ust_id=ust_id, dil_id=1, arsiv=arsiv)

        # AltId bulunamazsa bile en azından üst kategori genelini çek
        if not alt_ids:
            crawl_one(ust_id=ust_id, alt_id=None, count=count, arsiv=arsiv)
            continue

        # Her alt kategori için crawl
        for alt_id in alt_ids:
            crawl_one(ust_id=ust_id, alt_id=alt_id, count=count, arsiv=arsiv)


def get_alt_ids_from_getkategori_html(client: TuikClient, slug: str, ust_id: int) -> list[int]:
    """
    https://data.tuik.gov.tr/Kategori/GetKategori?p=<slug>-<ust_id>
    sayfasındaki alt kategori checkbox/value id'lerini toplar.
    """
    url = f"https://data.tuik.gov.tr/Kategori/GetKategori?p={slug}-{ust_id}"
    html = client.session.get(url, timeout=60).text

    soup = BeautifulSoup(html, "lxml")

    ids = set()

    # Önce input value'larından çek
    for inp in soup.select("input[value]"):
        v = (inp.get("value") or "").strip()
        if v.isdigit():
            n = int(v)
            if 1 <= n <= 2_000_000:
                ids.add(n)

    # Çok az bulduysa regex fallback
    if len(ids) < 5:
        for m in re.findall(r"\b(\d{2,7})\b", html):
            n = int(m)
            if 1 <= n <= 2_000_000:
                ids.add(n)

    return sorted(ids)



if __name__ == "__main__":
    ust_id = 100
    slug = "Nufus-ve-Demografi"

    client = TuikClient()
    alt_ids = get_alt_ids_from_getkategori_html(client, slug=slug, ust_id=ust_id)

    print(f"[ALT_IDS] ust_id={ust_id} count={len(alt_ids)} sample={alt_ids[:10]}", flush=True)

    for alt_id in alt_ids:
        crawl_one(ust_id=ust_id, alt_id=alt_id, slug=slug, count=50, arsiv=False)


