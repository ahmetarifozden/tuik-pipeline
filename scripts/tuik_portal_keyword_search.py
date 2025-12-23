#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import re
import time
from urllib.parse import quote, urljoin

import httpx

BASE = "https://data.tuik.gov.tr"
# TÜİK Search ekranındaki “Ana Kategoriler” (hepsi seçili)
MAIN_CATEGORY_IDS = [110, 102, 103, 105, 106, 107, 108, 109, 101]

# İndirme linkleri: ikisini de yakala
DL_RE = re.compile(
    r'(?P<u>(?:https?://data\.tuik\.gov\.tr)?/Bulten/(?:DownloadFile|DownloadIstatistikselTablo)\?[^"\'\s>]+)',
    re.IGNORECASE,
)

# Bülten içindeki diğer /Bulten/... sayfalarını bul (Tablolar vs)
BULTEN_ANY_RE = re.compile(r'(?P<u>/Bulten/[^"\'\s<>]+)', re.IGNORECASE)

def abs_url(u: str) -> str:
    return urljoin(BASE, u)

def request_with_retry(client: httpx.Client, method: str, url: str, **kwargs) -> httpx.Response:
    wait = 1.0
    last_exc = None
    for attempt in range(1, 6):
        try:
            r = client.request(method, url, **kwargs)
            if r.status_code >= 500:
                print(f"[HTTP-RETRY] attempt={attempt} status={r.status_code} wait={int(wait)}s")
                time.sleep(wait)
                wait *= 2
                continue
            r.raise_for_status()
            return r
        except Exception as e:
            last_exc = e
            print(f"[HTTP-RETRY] attempt={attempt} exc={type(e).__name__} wait={int(wait)}s")
            time.sleep(wait)
            wait *= 2
    raise last_exc  # type: ignore

def fetch_bulten_list(client: httpx.Client, keyword: str) -> list[str]:
    """
    Ürünlerde Ara -> Search sayfası akışını taklit eder:
    1) /Search/Search?text=... GET (cookie/oturum)
    2) /Search/GetHaberBultenleri POST (HTML döner)
    3) HTML içinden /Bulten/Index?p=... linklerini çıkarır
    """
    kw_enc = quote(keyword, safe="")

    # cookie/antiforgery otursun
    request_with_retry(client, "GET", f"{BASE}/Search/Search?text={kw_enc}")

    payload = {
        "SearchParameter": keyword,
        "Arsiv": "false",
    }

    # Ana kategoriler (hepsi seçili gibi)
    for i, cid in enumerate(MAIN_CATEGORY_IDS):
        payload[f"Kategoriler[{i}][Id]"] = str(cid)


    r = request_with_retry(
        client,
        "POST",
        f"{BASE}/Search/GetHaberBultenleri",
        data=payload,
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    html = r.text

    bulten_links = []
    for m in re.finditer(r'(/Bulten/Index\?p=[^"\'\s>]+)', html, re.IGNORECASE):
        bulten_links.append(abs_url(m.group(1)))

    # uniq + sıralı
    return sorted(set(bulten_links))

def extract_downloads_from_bulten(client: httpx.Client, bulten_url: str, max_inner_links: int = 30) -> list[str]:
    """
    1) Bülten sayfasını açar, indirme linklerini arar.
    2) Bulamazsa, sayfa içindeki diğer /Bulten/... linklerini (Tablolar vb.) gezip tekrar arar.
    """
    r = request_with_retry(client, "GET", bulten_url)
    html = r.text

    found = {abs_url(m.group("u")) for m in DL_RE.finditer(html)}
    if found:
        return sorted(found)

    # bülten içindeki diğer /Bulten/... linkleri
    inner_links = {abs_url(m.group("u")) for m in BULTEN_ANY_RE.finditer(html)}
    inner_links = list(inner_links)[:max_inner_links]

    for u in inner_links:
        try:
            rr = request_with_retry(client, "GET", u)
            found.update({abs_url(m.group("u")) for m in DL_RE.finditer(rr.text)})
        except Exception:
            continue

    return sorted(found)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keyword", required=True, help="Aranacak kelime (örn: ciro, çocuk)")
    ap.add_argument("--sleep", type=float, default=1.0, help="İstekler arası bekleme (rate-limit için)")
    ap.add_argument("--max", type=int, default=50, help="En fazla kaç bülten taransın")
    ap.add_argument("--show_all_bultens", action="store_true", help="İndirme olsun/olmasın tüm bültenleri listele")
    args = ap.parse_args()

    keyword = args.keyword.strip()
    kw_enc = quote(keyword, safe="")

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/html, */*; q=0.01",
        "Origin": BASE,
        "Referer": f"{BASE}/Search/Search?text={kw_enc}",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    with httpx.Client(headers=headers, timeout=30.0, follow_redirects=True) as client:
        bulten_urls = fetch_bulten_list(client, keyword)

        print(f"[HIT] keyword='{keyword}' -> {len(bulten_urls)} bülten bulundu")
        print("=" * 100)

        if not bulten_urls:
            return

        scanned = 0
        matched = 0

        for idx, b in enumerate(bulten_urls[: args.max], 1):
            scanned += 1
            time.sleep(args.sleep)

            dls = extract_downloads_from_bulten(client, b)

            # Senin istediğin format:
            # 01) bülten-url
            #     - indir-1
            #     - indir-2
            if dls:
                matched += 1
                print(f"{idx:02d}) {b}")
                for u in dls:
                    print(f"    - {u}")
                print("-" * 100)
            else:
                if args.show_all_bultens:
                    print(f"{idx:02d}) {b}")
                    print("    - (indirilebilir link bulunamadı)")
                    print("-" * 100)

        print(f"[DONE] scanned={scanned} matched_with_downloads={matched}")

if __name__ == "__main__":
    main()
