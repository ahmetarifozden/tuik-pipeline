import asyncio
import httpx
from bs4 import BeautifulSoup

URL = "https://data.tuik.gov.tr/Kategori/GetKategori?p=Nufus-ve-Demografi-109"

async def main():
    async with httpx.AsyncClient(
        timeout=30,
        follow_redirects=True,
        headers={"User-Agent": "tuik-pipeline/1.0"},
    ) as client:
        r = await client.get(URL)
        print("status:", r.status_code)
        print("len(html):", len(r.text))

        soup = BeautifulSoup(r.text, "lxml")

        # 1) Sayfadaki tüm linklerden "Kategori" geçenleri say
        links = [a["href"] for a in soup.find_all("a", href=True)]
        kat_links = [h for h in links if "Kategori" in h or "kategori" in h]
        print("total <a>:", len(links))
        print("kategori-like links:", len(kat_links))
        print("sample links:", kat_links[:10])

        # 2) Script src'lerini yaz
        scripts = [s["src"] for s in soup.find_all("script", src=True)]
        print("script src count:", len(scripts))
        print("script src sample:", scripts[:10])

        # 3) Inline scriptlerde 'Get' / 'api' / 'Json' geçen yerleri kaba arama
        text = r.text
        keywords = ["Get", "api", "Json", "Ajax", "fetch", "xhr", "/Kategori/", "/Istatistik/"]
        for k in keywords:
            print(k, "->", text.count(k))

if __name__ == "__main__":
    asyncio.run(main())
