import json, re, urllib.request

URL = "https://amscg.org/wp-json/wp/v2/pages/24"  # "Stanje na putevima" (AMSCG)

def fetch_items():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (RouteMeRight)"})
    data = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))
    html = data["content"]["rendered"]
    blocks = re.findall(r"(?s)<(?:p|li)[^>]*>(.*?)</(?:p|li)>", html)
    items = []
    for b in blocks:
        t = re.sub(r"(?s)<[^>]+>", " ", b)
        t = re.sub(r"&#8211;|&#8212;", "-", t)
        t = re.sub(r"&#822[0-1];|&#8217;|&quot;", '"', t)
        t = re.sub(r"&nbsp;| ", " ", t)
        t = re.sub(r"&amp;", "&", t)
        t = re.sub(r"\s+", " ", t).strip()
        if len(t) < 40:  # preskoci naslove/datum/prazno
            continue
        low = t.lower()
        if "frekvencija" in low or "uslovi za vo" in low:
            typ = "stanje"
        elif "obustava saobra" in low or "obustavlja" in low:
            typ = "zatvaranje"
        elif "zabranjuje" in low or "zabrana" in low:
            typ = "zabrana"
        elif "radov" in low or "rekonstrukcij" in low or "adaptacij" in low:
            typ = "radovi"
        else:
            continue  # kontakt/footer tekst
        road = re.search(r"\b([MR]-\d+)\b", t)
        m = re.search(r"dionic\w*\s+([A-ZĐŠČĆŽ][\w đšČćžŠĐČŽšćč\-]{2,40}?)(?:,| zbog| na | i |\.|$)", t)
        region = (road.group(1) + (" " + m.group(1).strip() if m else "")) if road else (m.group(1).strip() if m else "Crna Gora")
        items.append({
            "type": typ,
            "title": (t[:90] + "...") if len(t) > 90 else t,
            "detail": t,
            "region": region,
        })
    return items

if __name__ == "__main__":
    for it in fetch_items():
        print(it["type"], "|", it["region"], "|", it["title"])