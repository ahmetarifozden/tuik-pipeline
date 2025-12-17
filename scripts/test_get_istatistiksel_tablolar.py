from app.services.tuik.client import TuikClient

client = TuikClient()

html = client.get_istatistiksel_tablolar(
    ust_id=109,
    page=1,
    count=50
)

print(html[:2000])
