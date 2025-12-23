import re
import httpx
from bs4 import BeautifulSoup

URL = "https://data.tuik.gov.tr/Bulten/Index?p=Ciro-Endeksleri-Ekim-2025-54128"
BASE = "https://data.tuik.gov.tr"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
}

r = httpx.get(URL, headers=headers, timeout=30, follow_redirects=True)
r.raise_for_status()
html = r.text

print("status:", r.status_code, "len(html):", len(html))

soup = BeautifulSoup(html, "lxml")

links = []

# 1) href ile yakala
for a in soup.find_all("a", href=True):
    href = a["href"]
    if "/Bulten/DownloadIstatistikselTablo" in href and "p=" in href:
        text = a.get_text(" ", strip=True)
        if href.startswith("/"):
            href = BASE + href
        links.append((text, href))

# 2) regex ile yakala (JS içinde gömülü olabilir)
regex_hits = re.findall(r"/Bulten/DownloadIstatistikselTablo\?p=[^\"'\s<>]+", html)
for h in regex_hits:
    u = BASE + h
    links.append(("", u))

# unique
uniq = []
seen = set()
for t, u in links:
    if u not in seen:
        uniq.append((t, u))
        seen.add(u)

print("found:", len(uniq))
for i, (t, u) in enumerate(uniq, 1):
    print(f"{i:02d}) {t} {u}")
