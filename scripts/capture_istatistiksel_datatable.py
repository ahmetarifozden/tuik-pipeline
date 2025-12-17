from playwright.sync_api import sync_playwright

PAGE_URL = "https://data.tuik.gov.tr/Kategori/GetKategori?p=Nufus-ve-Demografi-109"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        def on_request(request):
            if request.resource_type in ("xhr", "fetch"):
                print("\nREQUEST:")
                print("URL:", request.url)
                print("METHOD:", request.method)

        def on_response(response):
            if response.request.resource_type in ("xhr", "fetch"):
                print("\nRESPONSE:")
                print("URL:", response.url)
                print("STATUS:", response.status)
                print("CONTENT-TYPE:", response.headers.get("content-type", ""))

        page.on("request", on_request)
        page.on("response", on_response)

        print("Opening page...")
        page.goto(PAGE_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        # Sayfadaki sekmelerden "İstatistiksel Tablolar" tab'ı: id="nav-profile-tab"
        print("Clicking Istatistiksel Tablolar tab...")
        page.click("#nav-profile-tab")
        page.wait_for_timeout(8000)

        browser.close()

if __name__ == "__main__":
    main()
