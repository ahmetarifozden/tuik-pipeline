from playwright.sync_api import sync_playwright

PAGE_URL = "https://data.tuik.gov.tr/Kategori/GetKategori?p=Nufus-ve-Demografi-109"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        def on_request(request):
            if request.resource_type in ("xhr", "fetch"):
                print("\nREQUEST:", request.method, request.url)
                if request.method == "POST":
                    print("POST DATA:", request.post_data)


        def on_response(response):
            if response.request.resource_type in ("xhr", "fetch"):
                print("RESPONSE:", response.status, response.url, response.headers.get("content-type", ""))

        page.on("request", on_request)
        page.on("response", on_response)

        print("Opening page...")
        page.goto(PAGE_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        print("Clicking tab...")
        page.click("#nav-profile-tab")
        page.wait_for_timeout(3500)

        # DataTables search input'u bekle
        page.wait_for_selector("#istatistikselTable_filter input", timeout=20000)

        # Arama yaz → bu kesin XHR tetikler
        page.fill("#istatistikselTable_filter input", "nufus")
        page.wait_for_timeout(8000)

        browser.close()

if __name__ == "__main__":
    main()
