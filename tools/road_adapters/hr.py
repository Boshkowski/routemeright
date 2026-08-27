# HAK - stanje na cestama, JSON API iza mape na hak.hr (TESTIRANO 2026-07-23, ~183 stavke)
# KLJUCNO: server vraca 404 bez gzip Accept-Encodinga (CDN sluzi samo gzip varijantu)
# PAZNJA: ne pisi "Accept-Encoding: gzip" u komentaru u prve 2 linije fajla -
#         Pythonov coding-cookie regex to protumaci kao encoding deklaraciju!
import urllib.request, urllib.error, json, gzip, re, html, time, http.client

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
        except http.client.IncompleteRead as e:
            # origin povremeno posalje Content-Length veci od tela; ono sto je stiglo
            # je najcesce ispravan gzip/JSON pa probamo sa delimicnim odgovorom
            raw = e.partial
        except (urllib.error.HTTPError, urllib.error.URLError, OSError):
            if i < tries - 1:
                time.sleep(3 * (i + 1))
            continue
        try:
            if raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            return json.loads(raw.decode("utf-8"))
        except Exception:
            if i < tries - 1:
                time.sleep(3 * (i + 1))
    return None

def _clean(s):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or ""))).strip()

def fetch_hak_items():
    # 0.9.95 (QA nalaz 93): kategorija koja padne se do sada tiho preskakala, a kolektor je
    # svejedno upisivao ok: true jer poziv nije bacio izuzetak. Zivo 26.8.: granicni-prijelazi
    # vracaju None u sva 4 pokusaja, a fajl kaze HR ok: true, 40 stavki - pa aplikacija nije
    # imala nacin ni da posteno cuti. Sada adapter prijavi STA mu je otpalo, kroz NEPOTPUNO.
    items = []
    pale = []
    for key, typ in CATS.items():
        resp = _get(BASE + key)
        if not resp:      # kategorija trenutno u refresh prozoru - preskoci
            pale.append(key)
            continue
        for grp in resp["data"].get("EventGroups") or []:
            for ev in grp.get("Events") or []:
                if key == "granicni-prijelazi-stanje":
                    # cekanja su u InfoboxContent HTML tabeli; red za ovaj prelaz
                    m = re.search(
                        r'gpime[^>]*><strong>\s*' + re.escape(ev["Title"]) +
                        r'.*?</tr>', ev.get("InfoboxContent") or "", re.S)
                    blok = m.group(0) if m else ""
                    waits = re.findall(r'class="gpUnos"[^>]*>([^<]*)<', blok)
                    w4 = [w.strip() or "-" for w in (waits + ["-"] * 4)[:4]]
                    detail = "cekanje ulaz auto/teretno: %s/%s, izlaz: %s/%s" % tuple(w4)
                    # KLJUCNO: starost se cita PO CELIJI ("T: 4.8.2026. 7:45:55"), ne po
                    # vremenu feeda - u istoj tabeli razlika ume da bude 4 sata.
                    stamps = re.findall(r"T:\s*([\d.]+\s*[\d:]+)", blok)
                    items.append({"type": typ, "title": ev["Title"],
                                  "detail": detail, "region": "granica",
                                  "border": {"ulaz_auto": w4[0], "ulaz_teretno": w4[1],
                                             "izlaz_auto": w4[2], "izlaz_teretno": w4[3],
                                             "ocitano": stamps[0] if stamps else None,
                                             "lat": ev.get("CoordinateY"), "lon": ev.get("CoordinateX"),
                                             "izvor": "HAK/MUP-HR", "za": "putnicka vozila"}})
                else:
                    kind = _clean(ev.get("Title"))  # npr. Zastoj / Radovi / Nesreca
                    detail = _clean(ev.get("Description") or ev.get("Details") or
                                    ev.get("LocationDescription"))
                    road = ev.get("Road") or grp.get("GroupID") or ""
                    zap = {
                        "type": typ + (" (" + kind + ")" if kind else ""),
                        "title": (road + " - " + kind).strip(" -"),
                        "detail": detail[:300],
                        "region": road or (ev.get("Region") or "HR")}
                    # KOORDINATA (19.8.): HAK je salje za svaki dogadjaj, a mi smo je do sada
                    # cuvali samo za granicne prelaze (gore) i bacali za radove - pa je
                    # aplikacija radove mogla da veze za rutu samo preko oznake puta.
                    # Provereno na zivom feedu: 23/23 dogadjaja ima CoordinateX/Y, 6 i
                    # CoordinateList (deonicu) u obliku [[lon,lat],...].
                    try:
                        lo, la = ev.get("CoordinateX"), ev.get("CoordinateY")
                        if lo not in (None, "") and la not in (None, ""):
                            zap["lon"], zap["lat"] = float(lo), float(la)
                    except (TypeError, ValueError):
                        pass
                    ln = ev.get("CoordinateList")
                    if isinstance(ln, list) and len(ln) >= 2:
                        zap["coords"] = ln
                    items.append(zap)
    globals()["NEPOTPUNO"] = pale   # kolektor ovo cita iz namespace-a adaptera
    return items

if __name__ == "__main__":
    its = fetch_hak_items()
    print(len(its), "stavki")
    for it in its[:10]:
        print(it)