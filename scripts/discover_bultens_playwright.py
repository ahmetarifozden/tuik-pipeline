import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

OUT = "config/bulten.yaml"
START_URLS = [
    "https://data.tuik.gov.tr/Bulten",
    "https://data.tuik.gov.tr",
]

async def main(limit: int = 200):
    found = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context()
        page = await ctx.new_page()

        for url in START_URLS:
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

            links = await page.query_selector_all("a[href]")
            for a in links:
                href = await a.get_attribute("href")
                if href and "/Bulten/Index?p=" in href:
                    if href.startswith("/"):
                        href = "https://data.tuik.gov.tr" + href
                    found.add(href)
                    if len(found) >= limit:
                        break

        await browser.close()

    Path("config").mkdir(exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("bulten_pages:\n")
        for u in sorted(found):
            f.write(f"  - {u}\n")

    print("saved:", OUT)
    print("count:", len(found))

if __name__ == "__main__":
    asyncio.run(main())
