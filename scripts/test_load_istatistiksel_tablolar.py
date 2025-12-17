from app.services.tuik.client import TuikClient

client = TuikClient()

# Büyük ihtimalle body boş ya da çok basit
resp = client.post("/Kategori/GetIstatistikselTablolar")

print("STATUS:", resp.status_code)
print(resp.headers.get("content-type"))
print(resp.text[:1500])
