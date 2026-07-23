# HAK - stanje na cestama, JSON API iza mape na hak.hr (TESTIRANO 2026-07-23, ~183 stavke)
# KLJUCNO: server vraca 404 bez gzip Accept-Encodinga (CDN sluzi samo gzip varijantu)
# PAZNJA: ne pisi "Accept-Encoding: gzip" u komentaru u prve 2 linije fajla -
#         Pythonov coding-cookie regex to protumaci kao encoding deklaraciju!
import urllib.request, urllib.error, json, gzip, re, html, time

BASE = "https://www.hak.hr/info/stanje-na-cestama-novo/events?subCategoryKey="
CATS = {  # subCategoryKey -> nas "type"
    "stanje-na-autocestama": "guzva/dogadjaj",
    "ceste-zatvorene-zbog-radova": "zatvaranje",
    "privremena-prometna-regulacija": "radovi",
    "dogadaji-na-cestama-ostalo": "dogadjaj",
    "granicni-prijelazi-stanje": "granicni-prelaz",
}

def _get(url, tries=4):
    # origin povremeno (u minutnim refresh prozorima) vrati 404 za pojedinu
    # kategoriju -> retry sa pauzom; posle svih pokusaja vrati None (preskoci).
    for i in range(tries):
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip"})
        try:
            raw = urllib.request.urlopen(req, timeout=30).read()
            if raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            return json.loads(raw.decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError):
            if i < tries - 1:
                time.sleep(3 * (i + 1))
    return None

def _clean(s):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or ""))).strip()

def fetch_hak_items():
    items = []
    for key, typ in CATS.items():
        resp = _get(BASE + key)
        if not resp:      # kategorija trenutno u refresh prozoru - preskoci
            continue
        for grp in resp["data"].get("EventGroups") or []:
            for ev in grp.get("Events") or []:
                if key == "granicni-prijelazi-stanje":
                    # cekanja su u InfoboxContent HTML tabeli; red za ovaj prelaz
                    m = re.search(
                        r'gpime[^>]*><strong>\s*' + re.escape(ev["Title"]) +
                        r'.*?</tr>', ev.get("InfoboxContent") or "", re.S)
                    waits = re.findall(r'class="gpUnos"[^>]*>([^<]*)<', m.group(0)) if m else []
                    detail = ("cekanje ulaz auto/teretno: %s/%s, izlaz: %s/%s" % tuple(
                        w.strip() or "-" for w in (waits + ["-"] * 4)[:4]))
                    items.append({"type": typ, "title": ev["Title"],
                                  "detail": detail, "region": "granica"})
                else:
                    kind = _clean(ev.get("Title"))  # npr. Zastoj / Radovi / Nesreca
                    detail = _clean(ev.get("Description") or ev.get("Details") or
                                    ev.get("LocationDescription"))
                    road = ev.get("Road") or grp.get("GroupID") or ""
                    items.append({
                        "type": typ + (" (" + kind + ")" if kind else ""),
                        "title": (road + " - " + kind).strip(" -"),
                        "detail": detail[:300],
                        "region": road or (ev.get("Region") or "HR")})
    return items

if __name__ == "__main__":
    its = fetch_hak_items()
    print(len(its), "stavki")
    for it in its[:10]:
        print(it)