import httpx

class TuikClient:
    BASE_URL = "https://data.tuik.gov.tr"

    def __init__(self):
        self.client = httpx.Client(
            base_url=self.BASE_URL,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )

    def get_istatistiksel_tablolar(
        self,
        ust_id: int,
        page: int = 1,
        count: int = 50,
        dil_id: int = 1,
        arsiv: bool = False
    ):
        data = {
            "UstId": ust_id,
            "DilId": dil_id,
            "Page": page,
            "Count": count,
            "Arsiv": str(arsiv).lower()
        }

        r = self.client.post(
            "/Kategori/GetIstatistikselTablolar",
            data=data
        )
        r.raise_for_status()
        return r.text
