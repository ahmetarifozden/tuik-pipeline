import httpx
import re

BUNDLE_URL = "https://data.tuik.gov.tr/bundle/js/main.min.js"

def main():
    js = httpx.get(BUNDLE_URL, timeout=30).text
    print("bundle size:", len(js))

    # fetch(...) geçen yerlerin etrafından örnek al (minify olduğu için endpoint nearby olur)
    hits = [m.start() for m in re.finditer(r"fetch\(", js)]
    print("fetch() count:", len(hits))

    # her hit için etrafından 200 karakter kesit al
    samples = []
    for idx in hits[:40]:  # ilk 40 yeter
        s = js[max(0, idx-120): idx+200]
        samples.append(s)

    # Bu kesitlerden URL benzeri parçaları yakala
    # /xxx/yyy, .php, .aspx, Get..., Post... gibi ipuçları
    pattern = r'(/[^"\'\s)]+)'
    candidates = set()
    for s in samples:
        for u in re.findall(pattern, s):
            # çok kısa/çok saçma şeyleri ele
            if len(u) < 5:
                continue
            # asset dosyalarını at
            if any(u.endswith(ext) for ext in [".js", ".css", ".png", ".jpg", ".svg", ".woff", ".woff2"]):
                continue
            candidates.add(u)

    print("\nEndpoint candidates (from fetch context):")
    for u in sorted(candidates)[:80]:
        print(u)

    # ayrıca "axios" ya da "XMLHttpRequest" arayalım
    for kw in ["axios", "XMLHttpRequest", "open(", "send("]:
        print(f"{kw} ->", js.count(kw))

if __name__ == "__main__":
    main()
