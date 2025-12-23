import asyncio
import yaml
from pathlib import Path
from playwright.async_api import async_playwright

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

async def extract_links_for_page(ctx, url: str) -> list[str]:
    page = await ctx.new_page()
    found = set()

    def on_request(req):
        u = req.url
        if "DownloadIstatistikselTablo?p=" in u:
            found.add(u)

    page.on("request", on_request)

    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)

    # bazen içerik frame içinde olabilir (sende 1 frame vardı)
    frames = page.frames

    for fr in frames:
        for sel in SELECTORS:
            try:
                els = await fr.query_selector_all(sel)
                for e in els[:80]:
                    try:
                        await e.scroll_into_view_if_needed()
                        await e.click(timeout=800, force=True)
                        await page.wait_for_timeout(400)
                    except:
                        pass
            except:
                pass

    await page.wait_for_timeout(1500)
    await page.close()
    return sorted(found)

async def main():
    cfg = load_yaml("config/bulten.yaml")
    pages = cfg.get("bulten_pages", [])
    if not pages:
        raise SystemExit("config/bulten.yaml içinde bulten_pages boş.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context()

        for url in pages:
            links = await extract_links_for_page(ctx, url)
            print("\n" + "=" * 90)
            print("BULTEN:", url)
            print("FOUND:", len(links))
            for i, u in enumerate(links, 1):
                print(f"{i:02d}) {u}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
