import asyncio
import re
from playwright.async_api import async_playwright

URL = "https://data.tuik.gov.tr/Bulten/Index?p=Ciro-Endeksleri-Ekim-2025-54128"
BASE = "https://data.tuik.gov.tr"

PATTERN = re.compile(r"/Bulten/DownloadIstatistikselTablo\?p=[A-Za-z0-9]+")  

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto(URL, wait_until="networkidle")

        links = set()

        # TÜM script tag'lerini tara
        scripts = await page.query_selector_all("script")
        for s in scripts:
            content = await s.inner_text()
            if not content:
                continue
            for m in PATTERN.findall(content):
                if m.startswith("/"):
                    links.add(BASE + m)
                else:
                    links.add(m)

        print("found:", len(links))
        for i, u in enumerate(sorted(links), 1):
            print(f"{i:02d}) {u}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
