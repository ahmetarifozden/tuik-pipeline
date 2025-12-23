#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from pathlib import Path
import yaml
from playwright.async_api import async_playwright

BASE = "https://data.tuik.gov.tr"

SELECTORS = [
    "a:has-text('XLS')",
    "a:has-text('Excel')",
    "button:has-text('XLS')",
    "button:has-text('Excel')",
    "[title*='xls' i]",
    "[aria-label*='xls' i]",
    "[title*='excel' i]",
    "[aria-label*='excel' i]",
    "img[alt*='xls' i]",
    "img[alt*='excel' i]",
    "img[src*='xls' i]",
    "img[src*='excel' i]",
    "i[class*='excel' i]",
    "i[class*='xls' i]",
]

def load_yaml(path: str) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))

def save_yaml(path: str, data: dict) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

async def extract_download_links(ctx, url: str, max_clicks: int = 120) -> list[str]:
    page = await ctx.new_page()
    found = set()

    def on_request(req):
        u = req.url
        # Genelleştirilmiş: DownloadFile + DownloadIstatistikselTablo + diğer Download* varyasyonları
        if "/Bulten/Download" in u:
            found.add(u)

    page.on("request", on_request)

    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_timeout(1500)

    clicks = 0

    # iframe içinde olabiliyor diye frames dolaşıyoruz
    for fr in page.frames:
        for sel in SELECTORS:
            try:
                els = await fr.query_selector_all(sel)
            except:
                continue

            for e in els[:250]:
                if clicks >= max_clicks:
                    break
                try:
                    await e.scroll_into_view_if_needed()
                    await e.click(timeout=800, force=True)
                    await page.wait_for_timeout(250)
                    clicks += 1
                except:
                    pass

    # isteklerin gelmesi için kısa bekleme
    await page.wait_for_timeout(800)
    await page.close()
    return sorted(found)

async def main():
    IN_YAML = "config/bulten.yaml"
    OUT_YAML = "config/downloads.yaml"

    HEADLESS = True      # debug için False
    MAX_BULTEN = 50      # yaml'dan kaç tane işleyecek
    MAX_CLICKS = 120     # sayfa başı max tıklama

    cfg = load_yaml(IN_YAML)
    pages = (cfg.get("bulten_pages", []) or [])[:MAX_BULTEN]

    if not pages:
        raise SystemExit(f"{IN_YAML} boş veya yok.")

    results = {
        "source_bulten_yaml": IN_YAML,
        "downloads": []  # list of {bulten_url, download_links}
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        ctx = await browser.new_context()

        total_downloads = 0

        for idx, bulten_url in enumerate(pages, 1):
            links = await extract_download_links(ctx, bulten_url, max_clicks=MAX_CLICKS)

            print("\n" + "=" * 110)
            print(f"[{idx}/{len(pages)}] {bulten_url}")
            print("DOWNLOAD_LINKS:", len(links))
            for i, u in enumerate(links, 1):
                print(f"{i:02d}) {u}")

            results["downloads"].append({
                "bulten_url": bulten_url,
                "download_links": links
            })
            total_downloads += len(links)

        await browser.close()

    save_yaml(OUT_YAML, results)
    print("\nDONE.")
    print("Bulten:", len(pages), "| Total download links:", total_downloads)
    print("YAML yazıldı:", OUT_YAML)

if __name__ == "__main__":
    asyncio.run(main())
