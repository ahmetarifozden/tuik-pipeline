from bs4 import BeautifulSoup
from app.services.tuik.client import TuikClient
from urllib.parse import urljoin

BASE = "https://data.tuik.gov.tr"

def main():
    client = TuikClient()
    html = client.get_istatistiksel_tablolar(ust_id=109, page=1, count=50)

    soup = BeautifulSoup(html, "lxml")
    table = soup.select_one("table#istatistikselTable")
    if not table:
        raise SystemExit("istatistikselTable not found")

    current_group = None
    rows = table.select("tbody tr")

    items = []
    for tr in rows:
        cls = " ".join(tr.get("class", []))

        # Grup satırı (kategori başlığı)
        if "dtrg-group" in cls:
            tds = tr.find_all("td")
            group_text = " ".join(td.get_text(" ", strip=True) for td in tds).strip()
            if group_text:
                current_group = group_text
            continue

        # Veri satırı
        tds = tr.find_all("td")
        if len(tds) < 3:
            continue

        title = tds[0].get_text(" ", strip=True)
        date_text = tds[1].get_text(" ", strip=True)

        a = tds[2].find("a", href=True)
        download_path = a["href"] if a else None
        download_url = urljoin(BASE, download_path) if download_path else None

        # boş title gelirse atla
        if not title:
            continue

        items.append({
            "group": current_group,
            "title": title,
            "date": date_text,
            "download_path": download_path,
            "download_url": download_url,
        })

    print("parsed items:", len(items))
    for it in items[:10]:
        print(it)

if __name__ == "__main__":
    main()
