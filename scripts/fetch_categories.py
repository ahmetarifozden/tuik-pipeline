from __future__ import annotations
from pathlib import Path

import sys
from urllib.parse import urljoin

import requests
import yaml
from bs4 import BeautifulSoup


BASE_URL = "https://data.tuik.gov.tr/"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_FILE = PROJECT_ROOT / "config" / "categories.yaml"


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


def extract_categories(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")

    urls: list[str] = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()

        # ❌ javascript linkleri alma
        if href.startswith("javascript:"):
            continue

        full_url = urljoin(BASE_URL, href)

        # ✅ SADECE kategori sayfaları
        if "/Kategori/GetKategori" not in full_url:
            continue

        # ❌ Dil switch / ana sayfa vs gelirse at
        if full_url == BASE_URL:
            continue

        if full_url in seen:
            continue

        seen.add(full_url)
        urls.append(full_url)

    return urls


def main() -> int:
    try:
        html = fetch_html(BASE_URL)
    except Exception as e:
        print(f"[ERR] Sayfa çekilemedi: {e}", file=sys.stderr)
        return 1

    cats = extract_categories(html)

    if not cats:
        print("[WARN] Kategori bulunamadı. Site DOM'u değişmiş olabilir.", file=sys.stderr)
        return 2

    data = {
        "categories_pages": cats
    }


    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            data,
            f,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )

    print(f"[OK] {len(cats)} kategori yazıldı -> {OUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
