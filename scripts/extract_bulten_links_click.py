import asyncio
from playwright.async_api import async_playwright

URL = "https://data.tuik.gov.tr/Bulten/Index?p=Ciro-Endeksleri-Ekim-2025-54128"

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

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        ctx = await browser.new_context()
        page = await ctx.new_page()

        real = set()

        def on_request(req):
            u = req.url
            if "DownloadIstatistikselTablo?p=" in u:
                real.add(u)

        page.on("request", on_request)

        await page.goto(URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        frames = page.frames
        print("frame count:", len(frames))
        print("page url:", page.url)

        for fr in frames:
            for sel in SELECTORS:
                try:
                    els = await fr.query_selector_all(sel)
                    for e in els[:50]:
                        try:
                            await e.scroll_into_view_if_needed()
                            await e.click(timeout=800, force=True)
                            await page.wait_for_timeout(600)
                        except:
                            pass
                except:
                    pass

        # biraz bekle ki request'ler gelsin
        await page.wait_for_timeout(2000)

        print("found:", len(real))
        for i, u in enumerate(sorted(real), 1):
            print(f"{i:02d}) {u}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
