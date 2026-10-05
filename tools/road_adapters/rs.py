import urllib.request, re

URL = "https://www.putevi-srbije.rs/stanje/novamapa/textfile.txt"  # latinica; textfile_cir.txt = cirilica

TYPE_MAP = {"RADOVI": "roadworks", "OBUSTAVE": "closure", "ZABRANE": "restriction", "ODRONI": "landslide"}

# 5.10.2026 (Boskova voznja Beograd-Bukulja): prva kolona fida ("point") je tacka na SLICI njihove mape (piksel, ne stepen),
# pa je do danas bacana. Pretvaranje u stepene: afina funkcija namestena na 15 tacaka vezanih za jedno mesto (mostovi,
# "u mestu X", "kod mesta X"), geokodiranih kroz Nominatim. Izmereno odstupanje: prosek 1,5 km, najvise 3,2 km (najgore su
# tacke koje su sire od tacke - planina, grad umesto mosta). Proba u Mercatoru i UTM 34 dala je VECE odstupanje, pa ostaje
# linearno u stepenima. Zato zapis nosi `tacnost_km`, i aplikacija ga nikad ne vezuje za rutu bez poklapanja broja puta.
LAT_K = (0.000586870038, 6.146395e-06, 46.269216043847)
LON_K = (-5.144656e-06, 0.000815148477, 18.403888250716)
TACNOST_KM = 3.5
# samoprovera: ako Putevi Srbije prerenderuju mapu, SVE tacke se pomere tiho - poznat zapis mora da padne gde treba
SIDRA = (("gazela", 44.80233, 20.44168), ("pančevački most", 44.82932, 20.49210))
SIDRO_MAX_KM = 4.0

def u_stepene(x, y):
    return (LAT_K[0] * x + LAT_K[1] * y + LAT_K[2], LON_K[0] * x + LON_K[1] * y + LON_K[2])

def _km(la1, lo1, la2, lo2):
    import math
    p = math.radians
    a = math.sin(p(la2 - la1) / 2) ** 2 + math.cos(p(la1)) * math.cos(p(la2)) * math.sin(p(lo2 - lo1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(a))

# 5.10.2026 (posle probe na zivom ruteru): tacka sa slike mape gresi i do 3,5 km, a zabranjena zona na pogresnom mestu ruter
# zaobidje sporednom ulicom i vrati se na zatvoreni put (izmereno: Lazarevac-Darosava se vracala na put 27 tacno u Kruseвici).
# Kad zapis IMENUJE mesto ("mesto X", "kod mesta X", "naseljeno mesto X", "u mestu X"), mesto se geokodira i, ako je do 8 km
# od tacke sa mape, ono je nova tacka (tacnost ~1 km). Kes imena ide kroz pozivaoca (collect_road_status cuva ga u fajlu).
MESTO_RE = re.compile(r"(?:naseljen[oi]m?\s+mest[ou]|u\s+mestu|kod\s+mesta|kod\s+sela|\bmesto|\bselo|u\s+selu)\s+([A-ZČĆŽŠĐ][\wčćžšđ-]+(?:\s+[A-ZČĆŽŠĐ][\wčćžšđ-]+)?)")
_CIR_LAT = str.maketrans({"К": "K", "А": "A", "Е": "E", "О": "O", "М": "M", "Т": "T", "а": "a", "е": "e", "о": "o", "к": "k"})   # urednici mesaju cirilicu u latinicu ("Кruševica")
MESTO_MAX_KM = 8.0
MESTO_TACNOST_KM = 1.0

def ime_mesta(tekst):
    m = MESTO_RE.search(str(tekst or "").translate(_CIR_LAT))
    if not m:
        return None
    ime = m.group(1).strip()
    return None if ime.lower() in ("srbija", "srbije", "km") else ime

def _geokodiraj(ime, la, lo, kes):
    """Najblize mesto tog imena u Srbiji do tacke sa mape (Nominatim, 1 zahtev u sekundi); None kad ga nema u krugu."""
    import json, time, urllib.parse
    if ime in kes:
        kand = kes[ime]
    else:
        url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({"q": ime + ", Srbija", "format": "json", "limit": 5, "countrycodes": "rs"})
        try:
            kand = [[float(r["lat"]), float(r["lon"])] for r in json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "RouteMeRight-robot/1.0 (routemeright.app)"}), timeout=15))]
        except Exception:
            return None   # bez kesa: sledeci krug proba ponovo
        kes[ime] = kand
        time.sleep(1.1)
    najb = min(kand, key=lambda k: _km(la, lo, k[0], k[1]), default=None)
    return najb if najb and _km(la, lo, najb[0], najb[1]) <= MESTO_MAX_KM else None

def preciziraj(items, kes):
    """Zapisima koji imenuju mesto zameni tacku sa mape geokodiranim mestom (ako je blizu). Vraca broj preciziranih."""
    n = 0
    for it in items:
        if "lat" not in it:
            continue
        ime = ime_mesta(it.get("title", "") + " " + it.get("detail", ""))
        if not ime:
            continue
        g = _geokodiraj(ime, it["lat"], it["lon"], kes)
        if g:
            it["lat"], it["lon"], it["tacnost_km"], it["mesto"] = round(g[0], 5), round(g[1], 5), MESTO_TACNOST_KM, ime
            n += 1
    return n

def _tacka(kol):
    try:
        x, y = (float(v) for v in kol.split(",")[:2])
        la, lo = u_stepene(x, y)
        if 41.8 <= la <= 46.3 and 18.7 <= lo <= 23.1:   # Srbija sa rubom; van toga je tacka pogresna
            return la, lo
    except (ValueError, TypeError):
        pass
    return None

def fetch_items():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    raw = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")
    items = []
    for line in raw.splitlines():
        cols = line.split("\t")
        if len(cols) < 3 or cols[0] == "point":
            continue
        title = cols[1].strip()
        detail = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", cols[2])).strip()
        m = re.match(r"([A-ZČĆŽŠĐ/]+)\s*:\s*(.*)", title)
        prefix, rest = (m.group(1), m.group(2)) if m else ("", title)
        typ = next((v for k, v in TYPE_MAP.items() if prefix.startswith(k)), "other")
        rm = None
        for txt in (rest, detail):
            rm = re.search(r"deonic[ae]\s+([A-ZČĆŽŠĐ][^,(.]{1,50}?)(?:\s+i\s+i?\s*raskrsnic|\s*[,(.]|$)", txt) \
                 or re.search(r"kod\s+(?:mesta\s+)?([A-ZČĆŽŠĐ][\wčćžšđ-]+)", txt)
            if rm:
                break
        region = rm.group(1).strip().rstrip(" i").strip() if rm else "Srbija"
        it = {"type": typ, "title": rest.strip(), "detail": detail, "region": region}
        t = _tacka(cols[0])
        if t:
            it["lat"], it["lon"], it["tacnost_km"] = round(t[0], 5), round(t[1], 5), TACNOST_KM
        items.append(it)
    items = samoprovera(items)
    kes = globals().get("MESTA_KES")   # kolektor ubacuje kes imena iz prethodnog fajla (vidi collect_road_status.run_adapter)
    n = preciziraj(items, kes if isinstance(kes, dict) else {})
    print(f"       rs.py: {n} zapisa precizirano po imenu mesta")
    return items

def samoprovera(items):
    """Pretvaranje se proverava nad zapisom koji uvek stoji u fidu (zabrana na Gazeli, Pancevacki most); kad sidro padne
    dalje od SIDRO_MAX_KM, koordinate se bacaju sa SVIH zapisa (bolje bez tacke nego sa pogresnom)."""
    provereno = False
    for ime, sla, slo in SIDRA:
        z = next((i for i in items if ime in i["title"].lower() and "lat" in i), None)
        if not z:
            continue
        provereno = True
        d = _km(z["lat"], z["lon"], sla, slo)
        if d > SIDRO_MAX_KM:
            print(f"[UPOZORENJE] rs.py: sidro '{ime}' palo {d:.1f} km od mesta - mapa Puteva Srbije je promenjena, koordinate se BACAJU")
            for i in items:
                for k in ("lat", "lon", "tacnost_km"):
                    i.pop(k, None)
        break
    if not provereno:
        print("[UPOZORENJE] rs.py: nijedno sidro nije u fidu - pretvaranje nije provereno ove ture")
    return items

if __name__ == "__main__":
    for it in fetch_items():
        print(it)