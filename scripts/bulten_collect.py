#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import re
from pathlib import Path
from urllib.parse import quote
import sys

import yaml
from playwright.async_api import async_playwright

BASE = "https://data.tuik.gov.tr"
SEARCH_URL = BASE + "/Search/Search?text={q}"

# Bülten sayfa url pattern'i (onclick içinde de geçebiliyor)
BULTEN_PAT = re.compile(r"/Bulten/Index\?p=[^\"'\s)]+", re.IGNORECASE)

def write_bulten_yaml(out_path: str, pages: list[str]) -> None:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    data = {"bulten_pages": pages}
    Path(out_path).write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

def absolutize(u: str) -> str:
    if not u:
        return ""
    if u.startswith("http"):
        return u
    if u.startswith("/"):
        return BASE + u
    return BASE + "/" + u

async def extract_bulten_urls_from_dom(page) -> list[str]:
    """
    Sayfadaki linkleri 3 yerden toplar:
    1) a[href] içinde /Bulten/Index?p=
    2) herhangi bir elementin onclick attribute'u içinde /Bulten/Index?p=
    3) data-href / data-url gibi attribute'larda /Bulten/Index?p=
    """
    js = r"""
    () => {
      const out = new Set();

      // 1) href
      document.querySelectorAll("a[href]").forEach(a => {
        const h = a.getAttribute("href") || "";
        if (h.includes("/Bulten/Index?p=")) out.add(h);
      });

      // 2) onclick
      document.querySelectorAll("[onclick]").forEach(el => {
        const oc = el.getAttribute("onclick") || "";
        if (oc.includes("/Bulten/Index?p=")) out.add(oc);
      });

      // 3) data-* url/href
      document.querySelectorAll("[data-href],[data-url],[data-link]").forEach(el => {
        ["data-href","data-url","data-link"].forEach(k => {
          const v = el.getAttribute(k) || "";
          if (v.includes("/Bulten/Index?p=")) out.add(v);
        });
      });

      return Array.from(out);
    }
    """
    raw = await page.evaluate(js)

    found = set()

    for item in raw:
        if not item:
            continue

        # item bazen direkt href olur, bazen onclick script olur
        # onclick içinden regex ile url çek
        if "/Bulten/Index?p=" in item:
            # item bir href ise direkt ekle
            if item.strip().startswith("/Bulten/Index?"):
                found.add(item.strip())
            else:
                # onclick içinden tüm /Bulten/Index?p=... parçalarını çıkar
                for m in BULTEN_PAT.finditer(item):
                    found.add(m.group(0))

    # absolute + unique + stabilize
    pages = [absolutize(u) for u in found]
    pages = sorted(set(pages))
    return pages

async def click_haber_bulteni_tab(page) -> None:
    """
    Ekrandaki 'Haber Bülteni' sekmesini aktif etmek için dener.
    Bazı sayfalarda zaten aktif olur ama garantiye alıyoruz.
    """
    candidates = [
        "text=Haber Bülteni",
        "a:has-text('Haber Bülteni')",
        "button:has-text('Haber Bülteni')",
        "li:has-text('Haber Bülteni')",
    ]
    for sel in candidates:
        try:
            el = await page.query_selector(sel)
            if el:
                await el.click(timeout=1500)
                await page.wait_for_timeout(600)
                return
        except:
            pass

async def try_next_page(page) -> bool:
    """
    Pagination varsa bir sonraki sayfaya geçmeyi dener.
    (Bazı sayfalarda '>' ya da 'Sonraki' olabilir.)
    """
    next_selectors = [
        "a:has-text('Sonraki')",
        "button:has-text('Sonraki')",
        "a[rel='next']",
        "button[rel='next']",
        "a:has-text('>')",
        "button:has-text('>')",
        "a[aria-label*='next' i]",
        "button[aria-label*='next' i]",
    ]
    for sel in next_selectors:
        try:
            el = await page.query_selector(sel)
            if el:
                await el.click(timeout=1500)
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_timeout(800)
                return True
        except:
            pass
    return False

async def collect_bultens(keyword: str, limit: int = 50, headless: bool = True, max_pages: int = 10) -> list[str]:
    """
    /Search/Search?text=... sayfasına gider,
    Haber Bülteni tabını açar,
    DOM’dan href + onclick + data-* içinden bülten linklerini toplar.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        ctx = await browser.new_context()
        page = await ctx.new_page()

        url = SEARCH_URL.format(q=quote(keyword))
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(1200)

        await click_haber_bulteni_tab(page)
        await page.wait_for_timeout(1200)

        seen = set()
        page_no = 0

        while len(seen) < limit and page_no < max_pages:
            page_no += 1

            # sonuçlar geç yükleniyorsa biraz daha bekle
            await page.wait_for_timeout(800)

            pages = await extract_bulten_urls_from_dom(page)
            for u in pages:
                if u not in seen:
                    seen.add(u)
                    if len(seen) >= limit:
                        break

            if len(seen) >= limit:
                break

            moved = await try_next_page(page)
            if not moved:
                break

        await browser.close()
        return sorted(seen)[:limit]

async def main():
    KEYWORD = sys.argv[1] if len(sys.argv) > 1 else "ihracat"
    LIMIT = 3
    HEADLESS = True      # debug için False yap
    OUT = "config/bulten.yaml"

    pages = await collect_bultens(KEYWORD, limit=LIMIT, headless=HEADLESS, max_pages=20)

    print(f'KEYWORD="{KEYWORD}" | bulten_found={len(pages)}')
    for i, u in enumerate(pages, 1):
        print(f"{i:03d}) {u}")

    write_bulten_yaml(OUT, pages)
    print(f"\nYAML yazıldı: {OUT}")

if __name__ == "__main__":
    asyncio.run(main())
