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
}
# 11.11.2026: kategorija "granicni-prijelazi-stanje" vraca 404 i samom HAK-u (u meniju je
# "omitted"). Tabela cekanja (izvor MUP) se sada ugradjuje u samu stranu stanja na cestama,
# u <div id="gpStatus">, bez koordinata - zato koordinate idu iz tablice ispod.
STRANA = "https://www.hak.hr/info/stanje-na-cestama/"

# Prelazi prema BiH, Srbiji i Crnoj Gori: kljuc = ime bez dijakritika, malim slovima (deo pre
# zagrade u HAK-ovoj tabeli, "Bajakovo (Batrovci)" -> "bajakovo"). Izvor: koordinate koje je HAK
# slao u dogadjajima do 10.2026, ostalo OSM barrier=border_control (11.11.2026). Prelaz koga
# nema ovde robot ispise u log ("BEZ KOORDINATE") - dopuni tablicu, inace ga app ne vidi na ruti.
KOORD = {
    "bajakovo": (45.0483, 19.0983), "tovarnik": (45.1565, 19.1716),
    "ilok": (45.2249, 19.4008), "ilok ii": (45.2165, 19.4218),
    "principovac": (45.1740, 19.3494), "erdut": (45.5145, 19.0782),
    "batina": (45.8427, 18.8492), "zupanja": (45.0464, 18.7035),
    "gunja": (44.8867, 18.8148), "slavonski samac": (45.0665, 18.4968),
    "svilaj": (45.1147, 18.3219), "slavonski brod": (45.1569, 18.0023),
    "stara gradiska": (45.1511, 17.2463), "gornji varos": (45.1632, 17.2050),
    "jasenovac": (45.2655, 16.9190), "hrvatska dubica": (45.1864, 16.8092),
    "hrvatska kostajnica": (45.2202, 16.5471), "dvor": (45.0502, 16.3716),
    "maljevac": (45.1976, 15.7924), "bogovolja": (45.0633, 15.7426),
    "pasin potok": (45.1763, 15.7771), "kordunski ljeskovac": (44.9755, 15.7826),
    "licko petrovo selo": (44.88, 15.76), "uzljebic": (44.7060, 15.9315),
    "licka kaldrma": (44.3284, 16.1949), "strmica": (44.1748, 16.2627),
    "kamensko": (43.6114, 16.9733), "arzano": (43.5807, 17.0036),
    "vinjani donji": (43.4223, 17.2743), "vinjani gornji": (43.4600, 17.2845),
    "prolog": (43.1909, 17.4275), "nova sela": (43.1235, 17.5610),
    "metkovic": (43.0506, 17.6614), "klek": (42.9401, 17.5793),
    "zaton doli": (42.8882, 17.6526), "cepikuce": (42.8703, 17.8496),
    "brgat": (42.6516, 18.1591), "gornji brgat": (42.6516, 18.1591),
    "karasovici": (42.4905, 18.4340), "vitaljina": (42.4232, 18.5137),
}
# ime za prikaz (sa dijakritikom) za prelaze koje tabela danas ne navodi
IME = {"bajakovo": "Bajakovo", "tovarnik": "Tovarnik", "ilok": "Ilok", "ilok ii": "Ilok II",
       "principovac": "Principovac", "erdut": "Erdut", "batina": "Batina", "zupanja": "Županja",
       "gunja": "Gunja", "slavonski samac": "Slavonski Šamac", "svilaj": "Svilaj", "slavonski brod": "Slavonski Brod",
       "stara gradiska": "Stara Gradiška", "gornji varos": "Gornji Varoš", "jasenovac": "Jasenovac",
       "hrvatska dubica": "Hrvatska Dubica", "hrvatska kostajnica": "Hrvatska Kostajnica", "dvor": "Dvor",
       "maljevac": "Maljevac", "bogovolja": "Bogovolja", "pasin potok": "Pašin Potok",
       "kordunski ljeskovac": "Kordunski Ljeskovac", "licko petrovo selo": "Ličko Petrovo Selo",
       "uzljebic": "Užljebić", "licka kaldrma": "Lička Kaldrma", "strmica": "Strmica", "kamensko": "Kamensko",
       "arzano": "Aržano", "vinjani donji": "Vinjani Donji", "vinjani gornji": "Vinjani Gornji", "prolog": "Prolog",
       "nova sela": "Nova Sela", "metkovic": "Metković", "klek": "Klek", "zaton doli": "Zaton Doli",
       "cepikuce": "Čepikuće", "brgat": "Brgat", "gornji brgat": "Gornji Brgat", "karasovici": "Karasovići",
       "vitaljina": "Vitaljina"}

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
                # cuvali samo za granicne prelaze i bacali za radove - pa je
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
    gr = fetch_granice()
    if gr is None:
        pale.append("granicni-prijelazi (gpStatus)")
    else:
        items.extend(gr)
    globals()["NEPOTPUNO"] = pale   # kolektor ovo cita iz namespace-a adaptera
    return items

def _get_html(url, tries=4):
    # ista otpornost kao _get (gzip, delimicno telo, ponovni pokusaj), ali vraca tekst
    for i in range(tries):
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip"})
        try:
            raw = urllib.request.urlopen(req, timeout=30).read()
        except http.client.IncompleteRead as e:
            raw = e.partial
        except (urllib.error.HTTPError, urllib.error.URLError, OSError):
            raw = None
        if raw:
            try:
                if raw[:2] == b"\x1f\x8b":
                    raw = gzip.decompress(raw)
                return raw.decode("utf-8", "replace")
            except Exception:
                pass
        if i < tries - 1:
            time.sleep(3 * (i + 1))
    return None

def _kljuc(ime):
    import unicodedata
    s = unicodedata.normalize("NFKD", ime.replace("đ", "dj").replace("Đ", "Dj"))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", s).strip()

def _koord(ime):
    k = _kljuc(ime)
    if k in KOORD:
        return KOORD[k]
    for kk, v in KOORD.items():   # "Gornji Brgat" / "Brgat", "Ilok II" / "Ilok"
        if k.startswith(kk + " ") or kk.startswith(k + " "):
            return v
    return None

_CELIJA = re.compile(r'class="gpUnos"[^>]*>([^<]*)<span class="gpDatmToolTip">([^<]*)</span>', re.S)

def _celija(vr, tip):
    """('2 h', 'L: 2 km T: 11.11.2026. 15:12:20') -> ('2 h', '11.11.2026. 15:12:20', 2.0)"""
    vr = vr.strip() or "-"
    t = re.search(r"T:\s*([\d.]+\s*[\d:]+)", tip)
    l = re.search(r"L:\s*([\d.,]+)\s*km", tip)
    km = float(l.group(1).replace(",", ".")) if l else None
    return vr, (t.group(1).strip() if t else None), km

def _novije(a, b):
    # "11.11.2026. 15:12:20" -> poredi se kao datum; None gubi
    def k(x):
        m = re.match(r"(\d+)\.(\d+)\.(\d{4})\.?\s*(\d+):(\d+)(?::(\d+))?", x or "")
        return tuple(int(g or 0) for g in (m.group(3), m.group(2), m.group(1), m.group(4), m.group(5), m.group(6))) if m else ()
    return a if k(a) >= k(b) else b

def fetch_granice():
    """Tabela cekanja sa strane stanja na cestama. None = strana ili tabela nisu stigle
    (kolektor to upise kao nepotpuno); prazna lista = tabela je tu, ali danas bez redova."""
    s = _get_html(STRANA)
    if not s or 'id="gpStatus"' not in s:
        return None
    blk = s[s.find('id="gpStatus"'):]
    out, bez = [], []
    for grp in re.finditer(r'<div class="gp([a-z_]+)">\s*<p class="gpTitle">(.*?)</p>(.*?)</table>', blk, re.S):
        for row in re.finditer(r'<td class="gpime">(.*?)</td>(.*?)</tr>', grp.group(3), re.S):
            pun = _clean(row.group(1))                     # "Bajakovo (Batrovci)"
            m = re.match(r"([^()]+?)\s*(?:\((.*?)\))?\s*$", pun)
            ime = (m.group(1) if m else pun).strip()
            susedni = (m.group(2) or "").strip() if m else ""
            c = [_celija(v, t) for v, t in _CELIJA.findall(row.group(2))]
            c = (c + [("-", None, None)] * 4)[:4]          # ulaz auto, ulaz teretno, izlaz auto, izlaz teretno
            # KLJUCNO: vreme merenja se cita PO CELIJI i samo iz celija za putnicka vozila -
            # 11.11. Bajakovo: ulaz auto 12:54, teretna 15:12 (ista tabela, 2 h razlike).
            ocitano = _novije(c[0][1], c[2][1]) if (c[0][1] or c[2][1]) else None
            ko = _koord(ime)
            if not ko:
                bez.append(ime)
            out.append({"type": "granicni-prelaz", "title": ime,
                        "detail": "cekanje ulaz auto/teretno: %s/%s, izlaz: %s/%s" % (c[0][0], c[1][0], c[2][0], c[3][0]),
                        "region": "granica",
                        "border": {"ulaz_auto": c[0][0], "ulaz_teretno": c[1][0],
                                   "izlaz_auto": c[2][0], "izlaz_teretno": c[3][0],
                                   "ocitano": ocitano,
                                   "ocitano_ulaz_auto": c[0][1], "ocitano_izlaz_auto": c[2][1],
                                   "kolona_ulaz_km": c[0][2], "kolona_izlaz_km": c[2][2],
                                   "susedni": susedni or None,
                                   "lat": ko[0] if ko else None, "lon": ko[1] if ko else None,
                                   "izvor": "HAK/MUP-HR", "za": "putnicka vozila"}})
    if bez:
        print("       HR granice BEZ KOORDINATE (dopuni KOORD u hr.py):", ", ".join(bez))
    if not out:
        print("       HR granice: tabela stigla, ali danas nema nijednog reda")
    # ZASTO SVI PRELAZI (11.11.): tabela nosi SAMO prelaze koji trenutno imaju podatak, a app kaci
    # cekanje na NAJBLIZI poznati prelaz do 15 km (graniceNaRuti). Bajakovo i Tovarnik su ~13 km
    # jedan od drugog: ruta preko Tovarnika bi pokazala Bajakovovih "1 h". Zato svaki prelaz iz
    # tablice ide u fajl - oni bez reda u tabeli bez izvora i bez cekanja (app kaze "nema podatka").
    zauzeto = {(g["border"]["lat"], g["border"]["lon"]) for g in out if g["border"]["lat"] is not None}
    for kljuc, (la, lo) in KOORD.items():
        if (la, lo) in zauzeto:
            continue   # vec iz tabele, ili isti prelaz pod drugim imenom (brgat / gornji brgat)
        zauzeto.add((la, lo))
        ime = IME.get(kljuc) or kljuc.title()
        out.append({"type": "granicni-prelaz", "title": ime, "detail": "cekanje: nema podatka",
                    "region": "granica",
                    "border": {"ulaz_auto": None, "izlaz_auto": None, "ulaz_teretno": None, "izlaz_teretno": None,
                               "ocitano": None, "lat": la, "lon": lo, "izvor": None, "za": "putnicka vozila"}})
    return out

if __name__ == "__main__":
    its = fetch_hak_items()
    print(len(its), "stavki", "NEPOTPUNO:", NEPOTPUNO)
    for it in its:
        if it.get("border"):
            print(it["title"], it["border"])