#!/usr/bin/env python3
import argparse
import re
import sys
import time
from urllib.parse import urljoin
from urllib.parse import quote
import httpx
from urllib.parse import urlencode

BASE = "https://data.tuik.gov.tr"

# Bülten URL'lerini yakalamak için (HTML içinde /Bulten/Index?... linkleri)
BULTEN_HREF_RE = re.compile(r'href="(?P<href>/Bulten/Index\?[^"]+)"', re.IGNORECASE)

# Bülten sayfasındaki indirme linkleri
DL_RE = re.compile(
    r'(?P<u>(?:https?://data\.tuik\.gov\.tr)?/Bulten/DownloadIstatistikselTablo\?[^"\'\s>]+)',
    re.IGNORECASE,
)
TABLO_URL_OK = re.compile(r"/Bulten/.*(Tablo|IstatistikselTablo|DownloadIstatistikselTablo)", re.IGNORECASE)
ANY_BULTEN_URL_RE = re.compile(r'(?P<u>/Bulten/[^"\'\s)<>]+)', re.IGNORECASE)
BULTEN_ANY_RE = re.compile(r'(?P<u>/Bulten/[^"\'\s<>]+)', re.IGNORECASE)

def abs_url(u: str) -> str:
    return urljoin(BASE, u)

def build_form_payload(keyword: str) -> dict:
    """
    En minimal payload ile deniyoruz.
    Eğer TÜİK tarafı kategori/alt kategori zorunlu kılarsa,
    buraya senin cURL'deki gibi Kategoriler/AltKategoriler listelerini de ekleriz.
    """
    return {
        "SearchParameter": keyword,
        "Arsiv": "false",
        # İstersen yıl filtresi ekleyebilirsin (UI'da seçili olanlar gibi):
        # "VeriYillari[]": ["2019","2020","2021","2022","2023","2024","2025"],
    }


def fetch_bulten_list(client: httpx.Client, keyword: str) -> list[str]:
    kw_enc = quote(keyword, safe="")

    # 1) Session/antiforgery cookie için sayfayı aç
    search_page = f"{BASE}/Search/Search?text={kw_enc}"
    request_with_retry(client, "GET", search_page)

    # 2) Arama sonuçlarını çeken endpoint
    url = f"{BASE}/Search/GetHaberBultenleri"

    payload = build_payload_from_curl(keyword)  # senin cURL payload fonksiyonun
    body = urlencode(payload)  # x-www-form-urlencoded string

    r = request_with_retry(
        client,
        "POST",
        url,
        content=body.encode("utf-8"),
        headers={
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        },
    )   
    html = r.text

    hrefs = {m.group("href") for m in BULTEN_HREF_RE.finditer(html)}
    return [urljoin(BASE, h) for h in sorted(hrefs)]


def extract_downloads_from_bulten(client, bulten_url: str) -> list[str]:
    r = request_with_retry(client, "GET", bulten_url)
    html = r.text

    found = {abs_url(m.group("u")) for m in DL_RE.finditer(html)}
    if found:
        return sorted(found)

    links = {abs_url(m.group("u")) for m in BULTEN_ANY_RE.finditer(html)}
    links = list(links)[:15]

    for u in links:
        try:
            rr = request_with_retry(client, "GET", u)
            found.update({abs_url(m.group("u")) for m in DL_RE.finditer(rr.text)})
        except Exception:
            continue

    return sorted(found)




def request_with_retry(client: httpx.Client, method: str, url: str, **kwargs) -> httpx.Response:

    """
    Network hatalarında ve 429/5xx gibi geçici HTTP hatalarında otomatik retry.
    """
    last_exc = None
    for attempt in range(1, 6):  # 5 deneme
        try:
            r = client.request(method, url, **kwargs)
            r.raise_for_status()
            return r

        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.RemoteProtocolError) as e:
            last_exc = e
            wait = min(2 ** attempt, 20)
            print(f"[NET-RETRY] attempt={attempt} wait={wait}s err={type(e).__name__}: {e}")
            time.sleep(wait)

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status in (429, 500, 502, 503, 504):
                wait = min(2 ** attempt, 20)
                print(f"[HTTP-RETRY] attempt={attempt} status={status} wait={wait}s")
                time.sleep(wait)
                last_exc = e
                continue
            raise
        except Exception as e:
            print(f"[UNEXPECTED] {type(e).__name__}: {repr(e)}")
            raise

    raise RuntimeError(f"Request failed after retries: {type(last_exc).__name__}: {last_exc}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keyword", required=True, help="Aranacak kelime (örn: çocuk)")
    ap.add_argument("--sleep", type=float, default=0.2, help="İstekler arası bekleme (rate-limit için)")
    ap.add_argument("--max", type=int, default=200, help="En fazla kaç bülten kontrol edilsin")
    args = ap.parse_args()

    keyword = args.keyword.strip()
    kw_enc = quote(keyword, safe="")

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/html, */*; q=0.01",
        "Origin": "https://data.tuik.gov.tr",
        "Referer": f"https://data.tuik.gov.tr/Search/Search?text={kw_enc}",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    # Daha dayanıklı ayarlar
    timeout = httpx.Timeout(60.0, connect=15.0)
    limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)

    with httpx.Client(
        base_url=BASE,
        headers=headers,
        timeout=timeout,
        limits=limits,
        follow_redirects=True,
        trust_env=True,  # proxy/cert env varsa kullanır
    ) as client:

        # (Öneri) İlk GET ile session/antiforgery cookie'leri oturtsun
        search_page = f"https://data.tuik.gov.tr/Search/Search?text={kw_enc}"
        request_with_retry(client, "GET", search_page)

        bulten_urls = fetch_bulten_list(client, keyword)  # içeride de retry kullanmanı öneriyorum
        if not bulten_urls:
            print(f"[NO RESULT] keyword='{keyword}' -> 0 bülten")
            return

        print(f"[HIT] keyword='{keyword}' -> {len(bulten_urls)} bülten bulundu")
        print("=" * 90)

        checked = 0
        matched = 0

        idx = 0
        matched = 0

        for b in bulten_urls[: args.max]:
            time.sleep(args.sleep)
            dls = extract_downloads_from_bulten(client, b)

            # İndirme linki yoksa yazma
            if not dls:
                continue

            matched += 1
            idx += 1

            print(f"{idx:02d}) {b}")
            for u in dls:
                print(f"    - {u}")
            print()  # boş satır

        print(f"[DONE] scanned={min(len(bulten_urls), args.max)} matched_with_downloads={matched}")


def build_payload_from_curl(keyword: str) -> list[tuple[str, str]]:
    data: list[tuple[str, str]] = []

    ust_ids = [110, 102, 103, 105, 106, 107, 108, 109, 101]
    for i, uid in enumerate(ust_ids):
        data.append((f"Kategoriler[{i}][Id]", str(uid)))

    alt_pairs = [
        (1070, 110),
        (1115, 102),
        (1097, 103),
        (1018, 105),
        (1086, 105),
        (1065, 106),
        (1121, 107),
        (1117, 107),
        (1007, 108),
        (1059, 109),
        (1125, 109),
        (1123, 109),
        (1110, 109),
        (1047, 109),
        (1060, 109),
        (1027, 109),
        (1068, 109),
        (1095, 101),
        (1040, 101),
    ]
    for i, (alt_id, ust_id) in enumerate(alt_pairs):
        data.append((f"AltKategoriler[{i}][AltId]", str(alt_id)))
        data.append((f"AltKategoriler[{i}][UstId]", str(ust_id)))

    for y in ["2019", "2020", "2021", "2022", "2023", "2024", "2025"]:
        data.append(("VeriYillari[]", y))

    data.append(("SearchParameter", keyword))
    data.append(("Arsiv", "false"))
    return data



if __name__ == "__main__":
    main()
