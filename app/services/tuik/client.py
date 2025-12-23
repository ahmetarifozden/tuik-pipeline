# app/services/tuik/client.py
import requests
from typing import Optional

class TuikClient:
    def __init__(self, base_url: str = "https://data.tuik.gov.tr", timeout: int = 60):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        # Tarayıcıya benzer User-Agent bazen işleri kolaylaştırır
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36",
        })

    def prime_category_session(self, ust_id: int, slug: str) -> str:
        """
        Tarayıcıda tıkladığın sayfa:
        /Kategori/GetKategori?p=<slug>-<ust_id>
        Bu GET çağrısı AspNetCore.Session / Antiforgery cookie'lerini set eder.
        """
        url = f"{self.base_url}/Kategori/GetKategori?p={slug}-{ust_id}"
        r = self.session.get(url, timeout=self.timeout)
        r.raise_for_status()
        return url  # referer olarak kullanacağız

    def get_istatistiksel_tablolar(
        self,
        ust_id: int,
        page: int = 1,
        count: int = 50,
        dil_id: int = 1,
        arsiv: bool = False,
        alt_idler: Optional[list[int]] = None,
        referer: Optional[str] = None,
    ) -> str:
        url = f"{self.base_url}/Kategori/GetIstatistikselTablolar"

        # DevTools'taki forma birebir
        payload: list[tuple[str, str]] = [
            ("UstId", str(ust_id)),
            ("DilId", str(dil_id)),
            ("Page", str(page)),
            ("Count", str(count)),
            ("Arsiv", "true" if arsiv else "false"),
        ]
        if alt_idler:
            for alt in alt_idler:
                payload.append(("AltIdler[]", str(alt)))

        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": self.base_url,
        }
        if referer:
            headers["Referer"] = referer

        r = self.session.post(url, data=payload, headers=headers, timeout=self.timeout)

        # Debug: hata olursa body’nin başını görelim
        if r.status_code >= 400:
            print("STATUS:", r.status_code)
            print("RESP_HEAD:", r.text[:300])
            r.raise_for_status()

        return r.text
