import asyncio
import httpx
from bs4 import BeautifulSoup

from app.core.db import SessionLocal
from app.models.category import Category

START_KEYS = [
    "Nufus-ve-Demografi-109",  # başlangıç (çalıştığını doğruladın)
]

BASE = "https://data.tuik.gov.tr"

def cat_url(key: str) -> str:
    return f"{BASE}/Kategori/GetKategori?p={key}"

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
        href = a["href"]
        if "/Kategori/GetKategori" in href and "p=" in href:
            key = href.split("p=", 1)[1].strip()
            name = a.get_text(strip=True)
            if key:
                out.append((key, name or key))
    # unique
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

async def main():
    async with httpx.AsyncClient(
        timeout=30,
        follow_redirects=True,
        headers={"User-Agent": "tuik-pipeline/1.0"},
    ) as client:
        queue = list(START_KEYS)
        seen = set()
        discovered = {}  # key -> name

        while queue:
            key = queue.pop(0)
            if key in seen:
                continue
            seen.add(key)

            url = cat_url(key)
            print("Fetching:", url)
            html = await fetch_html(client, url)

            links = extract_category_links(html)
            for k, name in links:
                if k not in discovered:
                    discovered[k] = name
                if k not in seen:
                    queue.append(k)

        print("Discovered categories:", len(discovered))

    # DB yaz
    db = SessionLocal()
    try:
        created = 0
        for k, name in discovered.items():
            _, is_new = upsert_category(db, k, name)
            created += 1 if is_new else 0
        db.commit()
        print(f"Saved. New: {created}, Total discovered: {len(discovered)}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
