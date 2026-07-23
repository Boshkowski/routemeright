import urllib.request, re, html

URL = "https://bihamk.ba/spi/stanje-na-cesti-u-bih/rss"

def fetch_bihamk():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")

    def strip_tags(s):
        s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
        s = re.sub(r"<[^>]+>", " ", s)
        return re.sub(r"\s+", " ", html.unescape(s)).strip()

    items = []
    # RSS description HTML: <div class="category"><h2>Sekcija</h2> + N x <div class="row"><h3>Naslov</h3><p>tekst</p>...
    for cat in re.split(r'<div class="category">', raw)[1:]:
        m = re.search(r"<h2>(.*?)</h2>", cat, re.S)
        region = strip_tags(m.group(1)) if m else "BiH"
        for row in re.split(r'<div class="row">', cat)[1:]:
            row = row.split("</div>")[0]
            t = re.search(r"<h3>(.*?)</h3>", row, re.S)
            title = strip_tags(t.group(1)) if t else ""
            detail = strip_tags(row[t.end():]) if t else strip_tags(row)
            if not (title or detail):
                continue
            low = (title + " " + detail).lower()
            if "grani" in region.lower():
                typ = "granicni_prelaz"
            elif any(k in low for k in ("radov", "sanacij", "rekonstrukcij", "izgradnj")):
                typ = "radovi"
            elif any(k in low for k in ("zatvoren", "obustavljen", "zabranjen", "ne mogu pro")):
                typ = "zatvaranje"
            elif any(k in low for k in ("pojacan", "pojačan", "zadrzavanj", "zadržavanj", "guzv", "gužv")):
                typ = "guzva"
            else:
                typ = "info"
            items.append({"type": typ, "title": title, "detail": detail, "region": region})
    return items

if __name__ == "__main__":
    for it in fetch_bihamk():
        print(it)