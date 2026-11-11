import json, re, urllib.request

# 11.11.2026: AMSCG je presao sa WordPress-a na nov sajt (Next.js na Vercel-u); stari
# wp-json/wp/v2/pages/24 od 14.10. vraca 403. Izvestaj Informativnog centra je sada u samoj
# strani, u <div class="w-full rich-text">, isti <p> blokovi kao ranije.
URL = "https://amscg.org/informacije/stanje-na-putevima"  # "Stanje na putevima" (AMSCG)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"

def fetch_items():
    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    strana = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    i = strana.find('class="w-full rich-text"')
    if i < 0:
        raise RuntimeError("AMSCG: nema bloka izvestaja (rich-text) - strana promenjena")
    html = strana[i:]
    kraj = re.search(r"</div>\s*</div>", html)   # izvestaj je jedan div sa <p> blokovima
    if kraj:
        html = html[:kraj.start()]
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
        elif "obustav" in low:   # 11.11.: "potpune obustave saobracaja" je ispadalo
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