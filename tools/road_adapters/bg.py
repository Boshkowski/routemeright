import urllib.request, re, html, json

URL = ("https://www.mvr.bg/gdgp/"
       "%D0%B8%D0%BD%D1%84%D0%BE%D1%80%D0%BC%D0%B0%D1%86%D0%B8%D0%BE%D0%BD%D0%B5%D0%BD-%D1%86%D0%B5%D0%BD%D1%82%D1%8A%D1%80/"
       "%D0%BF%D1%80%D0%B5%D1%81%D1%86%D0%B5%D0%BD%D1%82%D1%8A%D1%80/"
       "%D0%B5%D0%B6%D0%B5%D0%B4%D0%BD%D0%B5%D0%B2%D0%B5%D0%BD-%D1%82%D1%80%D0%B0%D1%84%D0%B8%D0%BA-%D0%BF%D0%BE-%D0%B3%D0%BA%D0%BF%D0%BF")

def fetch_bg_border_items():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (RouteMeRight)"})
    raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    m = re.search(r'class="page-content">(.*?)</div>', raw, re.S)
    body = m.group(1) if m else raw
    paras = []
    for p in re.findall(r"<p[^>]*>(.*?)</p>", body, re.S):
        p = html.unescape(re.sub(r"<[^>]+>", " ", p))
        p = re.sub(r"\s+", " ", p).strip()
        if p:
            paras.append(p)
    items, region = [], None
    for p in paras:
        if p.lower().startswith("the traffic at"):
            break  # dalje ide engleska kopija istog biltena
        if p.startswith("Трафикът на българските"):
            items.append({"type": "info", "title": "Бюлетин ГКПП (МВР)", "detail": p, "region": "BG"})
            continue
        mreg = re.match(r"Границата с\s*(.+?)\s*:?\s*$", p)
        if mreg:
            region = mreg.group(1).strip()
            continue
        low = p.lower()
        if "преустанов" in low or "затвор" in low or "затварян" in low or "спрян" in low:
            typ = "closure"
        elif "ремонт" in low:
            typ = "roadworks"
        elif "интензивен" in low or "засилен" in low or "изчакване" in low:
            typ = "congestion"
        else:
            typ = "border-status"
        items.append({
            "type": typ,
            "title": p[:90] + ("..." if len(p) > 90 else ""),
            "detail": p,
            "region": "Граница с " + (region or "?"),
        })
    return items

if __name__ == "__main__":
    print(json.dumps(fetch_bg_border_items(), ensure_ascii=False, indent=1))