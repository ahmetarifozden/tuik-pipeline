import re
import httpx
from bs4 import BeautifulSoup

URL = "https://data.tuik.gov.tr/Bulten/Index?p=Ciro-Endeksleri-Ekim-2025-54128"
BASE = "https://data.tuik.gov.tr"

html = httpx.get(URL, timeout=30, follow_redirects=True).text
soup = BeautifulSoup(html, "lxml")

links = []
# 1) normal href
for a in soup.find_all("a", href=True):
    href = a["href"]
    if "/Bulten/DownloadIstatistikselTablo" in href and "p=" in href:
        text = a.get_text(" ", strip=True)
        links.append((text, BASE + href if href.startswith("/") else href))

# 2) sayfada href yoksa regex ile yakala (JS içinde gömülü olabilir)
if not links:
    for m in re.findall(r'\/Bulten\/DownloadIstatistikselTablo\?p=[^"\']+', html):
        links.append(("", BASE + m))

print("found:", len(links))
for i, (t, u) in enumerate(links, 1):
    print(i, t, u)
