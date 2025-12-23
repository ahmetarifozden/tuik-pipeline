import asyncio
from pathlib import Path
import yaml
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

def norm(s: str) -> str:
    return (s or "").lower()

def match_keywords(text: str, keywords: list[str], mode: str) -> bool:
    t = norm(text)
    keys = [k.strip().lower() for k in keywords if k and k.strip()]
    if not keys:
        return False
    if mode == "all":
        return all(k in t for k in keys)
    return any(k in t for k in keys)  # any

async def extract_download_links(ctx, url: str, max_clicks: int = 120) -> list[str]:
    page = await ctx.new_page()
    found = set()

    def on_request(req):
        u = req.url
        if "DownloadIstatistikselTablo?p=" in u:
            found.add(u)

    page.on("request", on_request)

    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)

    clicks = 0
    for fr in page.frames:
        for sel in SELECTORS:
            try:
                els = await fr.query_selector_all(sel)
            except:
                continue
            for e in els[:200]:
                if clicks >= max_clicks:
                    break
                try:
                    await e.scroll_into_view_if_needed()
                    await e.click(timeout=800, force=True)
                    await page.wait_for_timeout(350)
                    clicks += 1
                except:
                    pass

    await page.wait_for_timeout(1000)
    await page.close()
    return sorted(found)

async def main():
    cfg = load_yaml("config/bulten_search.yaml")

    search = cfg.get("search", {})
    keywords = search.get("keywords", [])
    match_mode = search.get("match_mode", "any")
    headless = bool(search.get("headless", True))
    max_bulten = int(search.get("max_bulten", 50))
    max_clicks = int(search.get("max_clicks", 120))

    inputs = cfg.get("inputs", {})
    bulten_list_path = inputs.get("bulten_list_path", "config/bulten.yaml")

    bcfg = load_yaml(bulten_list_path)
    pages = bcfg.get("bulten_pages", []) or []
    pages = pages[:max_bulten]

    if not pages:
        raise SystemExit(f"{bulten_list_path} boş veya yok.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        ctx = await browser.new_context()

        hit_count = 0

        for idx, url in enumerate(pages, 1):
            page = await ctx.new_page()
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(1500)

            # Keyword kontrolü: title + içerik text
            title = await page.title()
            body_text = ""
            try:
                body_text = await page.inner_text("body")
            except:
                pass

            ok = match_keywords(title + "\n" + body_text, keywords, match_mode)
            await page.close()

            if not ok:
                continue

            hit_count += 1
            links = await extract_download_links(ctx, url, max_clicks=max_clicks)

            print("\n" + "=" * 110)
            print(f"HIT #{hit_count} | [{idx}/{len(pages)}] {url}")
            print("KEYWORDS:", keywords, "| mode:", match_mode)
            print("DOWNLOAD_LINKS:", len(links))
            for i, u in enumerate(links, 1):
                print(f"{i:02d}) {u}")

        print("\nDONE. Total hits:", hit_count)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
