import asyncio
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs

import httpx
import yaml
from bs4 import BeautifulSoup

from app.core.db import SessionLocal
from app.models.category import Category

BASE = "https://data.tuik.gov.tr"

# Proje kökünü scripts/ altından bul
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATEGORIES_YAML = PROJECT_ROOT / "config" / "categories.yaml"


def cat_url(key: str) -> str:
    return f"{BASE}/Kategori/GetKategori?p={key}"


def key_from_url(u: str) -> str | None:
    """
    https://data.tuik.gov.tr/Kategori/GetKategori?p=... URL'sinden p parametresini alır.
    """
    try:
        parsed = urlparse(u)
        qs = parse_qs(parsed.query)
        p = qs.get("p", [None])[0]
        return p
    except Exception:
        return None


def load_start_keys() -> list[str]:
    if not CATEGORIES_YAML.exists():
        raise FileNotFoundError(f"categories.yaml bulunamadı: {CATEGORIES_YAML}")

    with open(CATEGORIES_YAML, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    urls = data.get("categories_pages", [])
    if not isinstance(urls, list) or not urls:
        raise ValueError("categories.yaml içinde categories_pages listesi boş/yanlış formatta.")

    keys = []
    for u in urls:
        k = key_from_url(str(u))
        if k:
            keys.append(k)

    # unique ama sırası korunsun
    uniq = []
    seen = set()
    for k in keys:
        if k not in seen:
            seen.add(k)
            uniq.append(k)
    return uniq


async def fetch_html(client: httpx.AsyncClient, url: str) -> str:
    r = await client.get(url)
    r.raise_for_status()
    return r.text


def extract_category_links(html: str) -> list[tuple[str, str]]:
    """
    Sayfa içinden /Kategori/GetKategori?p=... linklerini ve isimlerini çıkar.
    """
    soup = BeautifulSoup(html, "lxml")
    out = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()

        # javascript linkleri ele
        if href.startswith("javascript:"):
            continue

        # relative olabilir
        full = urljoin(BASE, href)

        if "/Kategori/GetKategori" not in full:
            continue

        k = key_from_url(full)
        if not k:
            continue

        name = a.get_text(" ", strip=True)
        out.append((k, name or k))

    # unique (ilk görüleni koru)
    uniq = {}
    for k, n in out:
        if k not in uniq:
            uniq[k] = n
    return list(uniq.items())


def upsert_category(db, tuik_key: str, name: str):
    obj = db.query(Category).filter(Category.tuik_key == tuik_key).first()
    if obj:
        obj.name = name
        return obj, False
    obj = Category(tuik_key=tuik_key, name=name)
    db.add(obj)
    return obj, True


async def crawl_all(start_keys: list[str]) -> dict[str, str]:
    """
    Birden fazla start key’den başlayıp tüm alt kategorileri keşfeder.
    Çıktı: discovered dict (key -> name)
    """
    async with httpx.AsyncClient(
        timeout=30,
        follow_redirects=True,
        headers={"User-Agent": "tuik-pipeline/1.0"},
    ) as client:

        queue = list(start_keys)
        seen = set()
        discovered: dict[str, str] = {}

        total_fetch = 0

        while queue:
            key = queue.pop(0)
            if key in seen:
                continue
            seen.add(key)

            url = cat_url(key)
            total_fetch += 1
            print(f"[{total_fetch}] Fetching: {url}")

            html = await fetch_html(client, url)
            links = extract_category_links(html)

            # sayfanın kendisini de discovered'a eklemek istersen burada isim yok,
            # bu yüzden sadece linklerden gelen isimleri topluyoruz.

            for k, name in links:
                if k not in discovered:
                    discovered[k] = name
                if k not in seen:
                    queue.append(k)

        print(f"[DONE] Total fetched pages: {total_fetch}")
        return discovered


async def main():
    start_keys = load_start_keys()
    print(f"[START] categories.yaml içinden başlangıç kategori sayısı: {len(start_keys)}")

    discovered = await crawl_all(start_keys)

    print(f"[FOUND] Toplam keşfedilen alt kategori sayısı (unique key): {len(discovered)}")

    # DB yaz
    with SessionLocal() as db:
        created = 0
        updated = 0

        for k, name in discovered.items():
            _, is_new = upsert_category(db, k, name)
            if is_new:
                created += 1
            else:
                updated += 1

        db.commit()

    print(f"[SAVED] DB yazıldı. New: {created}, Updated: {updated}, Total discovered: {len(discovered)}")


if __name__ == "__main__":
    asyncio.run(main())
