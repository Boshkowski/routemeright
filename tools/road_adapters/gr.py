import json, re, html, urllib.request, xml.etree.ElementTree as ET

UA = {"User-Agent": "Mozilla/5.0 (RouteMeRight traffic fetcher)"}

def _get(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read()

def _clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()

def _classify(text):
    t = text.upper()
    if re.search(r"ΔΙΑΚΟΠ|ΚΛΕΙΣΤ|ΑΠΟΚΛΕΙΣΜ", t): return "closure"
    if re.search(r"ΕΡΓΑΣΙ|ΣΥΝΤΗΡΗΣ|ΑΣΦΑΛΤΟΣΤΡ|ΡΥΘΜΙΣ", t): return "roadworks"
    if re.search(r"ΚΙΝΗΤΟΠΟΙΗΣ|ΚΥΚΛΟΦΟΡ", t): return "traffic"
    return "info"

def fetch_greece_traffic():
    items = []
    # 1) Attiki Odos (novi operater Nea Attiki Odos) - WP REST JSON, zive kykl. rythmiseis
    try:
        url = ("https://www.naodos.gr/wp-json/wp/v2/posts"
               "?per_page=10&_fields=title,excerpt,date,link")
        for p in json.loads(_get(url)):
            title = _clean(p["title"]["rendered"])
            detail = _clean(p["excerpt"]["rendered"])[:300] + " | " + p.get("link", "")
            items.append({"type": _classify(title + " " + detail),
                          "title": title, "detail": detail,
                          "region": "Atika (Atinski ring, A6/A64)"})
    except Exception as e:
        items.append({"type": "error", "title": "naodos.gr fail",
                      "detail": str(e), "region": "Atika"})
    # 2) RSS rezerve: Aegean Motorway (A1 Maliakos-Kleidi) + Egnatia Odos (A2, sever)
    for url, region in [
        ("https://www.aegeanmotorway.gr/feed/", "A1 Maliakos-Kleidi (centralna Grcka)"),
        ("https://egnatia.eu/category/deltia-typou/feed/", "A2 Egnatia (severna Grcka)"),
    ]:
        try:
            root = ET.fromstring(_get(url))
            for it in root.iter("item"):
                title = _clean(it.findtext("title", ""))
                desc = _clean(it.findtext("description", ""))[:300]
                date = it.findtext("pubDate", "")
                link = it.findtext("link", "")
                items.append({"type": _classify(title + " " + desc),
                              "title": title,
                              "detail": (date + " - " + desc + " | " + link).strip(" -"),
                              "region": region})
        except Exception as e:
            items.append({"type": "error", "title": url, "detail": str(e), "region": region})
    return items

if __name__ == "__main__":
    for x in fetch_greece_traffic():
        print(json.dumps(x, ensure_ascii=False))