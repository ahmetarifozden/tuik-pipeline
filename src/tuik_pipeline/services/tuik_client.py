import requests
from typing import Optional
from src.tuik_pipeline.core.logging import get_logger

logger = get_logger(__name__)

class TuikClient:
    def __init__(self, base_url: str = "https://data.tuik.gov.tr", timeout: int = 60):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        # Mimic a browser User-Agent
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36",
        })

    def prime_category_session(self, parent_id: int, slug: str) -> str:
        """
        Simulates visiting the category page:
        /Kategori/GetKategori?p=<slug>-<parent_id>
        This GET request sets necessary AspNetCore.Session / Antiforgery cookies.
        """
        url = f"{self.base_url}/Kategori/GetKategori?p={slug}-{parent_id}"
        r = self.session.get(url, timeout=self.timeout)
        r.raise_for_status()
        return url  # Return to use as Referer

    def get_statistical_tables(
        self,
        parent_id: int,
        page: int = 1,
        count: int = 50,
        lang_id: int = 1,
        archive: bool = False,
        child_ids: Optional[list[int]] = None,
        referer: Optional[str] = None,
    ) -> str:
        """
        Fetches the HTML content of the statistical tables table (Ajax request).
        """
        url = f"{self.base_url}/Kategori/GetIstatistikselTablolar"

        # Form data matching the actual browser request
        payload: list[tuple[str, str]] = [
            ("UstId", str(parent_id)),
            ("DilId", str(lang_id)),
            ("Page", str(page)),
            ("Count", str(count)),
            ("Arsiv", "true" if archive else "false"),
        ]
        if child_ids:
            for child in child_ids:
                payload.append(("AltIdler[]", str(child)))

        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": self.base_url,
        }
        if referer:
            headers["Referer"] = referer

        r = self.session.post(url, data=payload, headers=headers, timeout=self.timeout)

        if r.status_code >= 400:
            logger.error(f"Status: {r.status_code}, Response Head: {r.text[:300]}")
            r.raise_for_status()

        return r.text
