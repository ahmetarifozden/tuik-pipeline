import asyncio
import re
from urllib.parse import quote
from playwright.async_api import async_playwright

BASE = "https://data.tuik.gov.tr"

# Excel/XLS butonu yakalamak için seninkiyle aynı selector mantığı
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

# Bülten linklerini yakalamak için: /Bulten/Index?p=... veya /Bulten/Index?...
BULTEN_RE = re.compile(r"/Bulten/Index\?p=[^\"'\s>]+", re.IGNORECASE)

def absolutize(href: str) -> str:
    if not href:
        return ""
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return BASE + href
    return BASE + "/" + href

async def collect_bulten_urls_from_search(ctx, keyword: str, limit: int = 30) -> list[str]:
    """
    1) Keyword ile TÜİK'te bülten arayıp bülten URL'lerini toplar.
    Not: Arama sayfasının yapısına göre 2 yöntem dener.
    """
    page = await ctx.new_page()
    urls = []

    # Yöntem-1: Query param ile arama (çoğu sitede çalışır)
    # TÜİK'te tam endpoint değişebilir; çalışmıyorsa Yöntem-2 devreye girer.
    candidate_search_urls = [
        f"{BASE}/Search/Search?text={quote(keyword)}",
        f"{BASE}/Search/Search?query={quote(keyword)}",
        f"{BASE}/Search?text={quote(keyword)}",
        f"{BASE}/Search?query={quote(keyword)}",
    ]

    loaded = False
    for surl in candidate_search_urls:
        try:
            await page.goto(surl, wait_until="domcontentloaded")
            await page.wait_for_timeout(1200)
            # Sayfada bülten linki var mı hızlı kontrol:
            html = await page.content()
            if "Bulten/Index" in html:
                loaded = True
                break
        except:
            continue

    # Yöntem-2: UI üstünden arama (input'a yaz, enter bas)
    # Eğer Yöntem-1 olmadıysa burada şansımız var.
    if not loaded:
        await page.goto(BASE, wait_until="domcontentloaded")
        await page.wait_for_timeout(1200)

        # olası arama kutusu selector’ları (genel)
        search_selectors = [
            "input[type='search']",
            "input[placeholder*='Ara' i]",
            "input[placeholder*='Search' i]",
            "input[name*='search' i]",
            "input[id*='search' i]",
        ]

        box = None
        for ss in search_selectors:
            try:
                box = await page.query_selector(ss)
                if box:
                    break
            except:
                pass

        if not box:
            await page.close()
            return []

        await box.fill(keyword)
        await box.press("Enter")
        await page.wait_for_timeout(1500)

    # Sonuç sayfasından bülten URL’lerini çıkar
    # 1) Direkt linklerden
    anchors = await page.query_selector_all("a[href*='/Bulten/Index']")
    for a in anchors:
        href = await a.get_attribute("href")
        u = absolutize(href)
        if u and u not in urls:
            urls.append(u)
        if len(urls) >= limit:
            break

    # 2) Eğer anchor yakalayamazsak HTML regex fallback
    if not urls:
        html = await page.content()
        for m in BULTEN_RE.finditer(html):
            u = absolutize(m.group(0))
            if u and u not in urls:
                urls.append(u)
            if len(urls) >= limit:
                break

    await page.close()
    return urls[:limit]

async def extract_download_links_by_click(ctx, bulten_url: str, max_clicks: int = 120) -> list[str]:
    """
    2) Bülten sayfasına girer.
    Excel/XLS ikonlarına tıklar.
    Ağ isteklerinden /Bulten/Download... linklerini yakalar.
    """
    page = await ctx.new_page()
    found = set()

    def on_request(req):
        u = req.url
        # Senin script’in çekirdeği: network’ten yakala
        if "/Bulten/Download" in u:
            found.add(u)

    page.on("request", on_request)

    await page.goto(bulten_url, wait_until="domcontentloaded")
    await page.wait_for_timeout(1500)

    clicks = 0
    # Frame'lerde dolaşma: iframe içinde olabiliyor
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

    # Biraz bekleyelim ki istekler gelsin
    await page.wait_for_timeout(800)
    await page.close()
    return sorted(found)

async def run(keyword: str, max_bulten: int = 20, max_clicks: int = 120, headless: bool = True):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        ctx = await browser.new_context()

        bultens = await collect_bulten_urls_from_search(ctx, keyword, limit=max_bulten)
        print(f'\nKEYWORD="{keyword}" | bulten_found={len(bultens)}')

        for i, bu in enumerate(bultens, 1):
            links = await extract_download_links_by_click(ctx, bu, max_clicks=max_clicks)
            print("\n" + "=" * 110)
            print(f"[{i}/{len(bultens)}] {bu}")
            print("DOWNLOAD_LINKS:", len(links))
            for k, u in enumerate(links, 1):
                print(f"{k:02d}) {u}")

        await browser.close()

if __name__ == "__main__":
    # Headless=False yaparsan ekranda görürsün (debug için çok iyi)
    asyncio.run(run(keyword="ciro", max_bulten=20, max_clicks=120, headless=True))
