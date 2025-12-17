from app.services.tuik.client import TuikClient

client = TuikClient()
resp = client.post("/Kategori/GetIstatistikselTablolar")

print("STATUS:", resp.status_code)
print("CT:", resp.headers.get("content-type"))

# Dosyaya yaz
with open("istatistiksel.html", "w", encoding="utf-8") as f:
    f.write(resp.text)

print("Wrote istatistiksel.html")
