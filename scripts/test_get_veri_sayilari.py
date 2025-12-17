from app.services.tuik.client import TuikClient

client = TuikClient()

resp = client.post("/Kategori/GetVeriSayilari")
print("STATUS:", resp.status_code)
print(resp.text[:1000])
