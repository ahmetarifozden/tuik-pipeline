import re
from bs4 import BeautifulSoup
from app.services.tuik.client import TuikClient

client = TuikClient()
resp = client.post("/Kategori/GetIstatistikselTablolar")

html = resp.text

# 1) Script içindeki url: "..." veya "sAjaxSource": "..."
patterns = [
    r'ajax\s*:\s*{[^}]*url\s*:\s*"([^"]+)"',
    r'ajax\s*:\s*"([^"]+)"',
    r'"sAjaxSource"\s*:\s*"([^"]+)"',
    r'url\s*:\s*"(/[^"]+)"',
]

found = set()
for pat in patterns:
    for m in re.findall(pat, html, flags=re.IGNORECASE | re.DOTALL):
        if m.startswith("/"):
            found.add(m)
        elif "http" in m:
            found.add(m)

print("Found candidates:")
for u in sorted(found):
    print(u)

# 2) Hiç bulamazsak: script bloklarını basitçe yazdıralım (ilk 1500 char)
soup = BeautifulSoup(html, "lxml")
scripts = soup.find_all("script")
print("\nscript blocks:", len(scripts))
if scripts:
    print("\nFirst script snippet:\n", scripts[0].get_text()[:1500])
