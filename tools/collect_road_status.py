#!/usr/bin/env python3
"""Sakuplja stanje na putevima (10 zemalja) + Meteoalarm upozorenja -> data/road_status.json.
Pokrece ga GitHub Action (.github/workflows/road-status.yml) 5x dnevno.
Adapteri u tools/road_adapters/ su testirani uzivo 2026-07-23 (multi-agent provera).
Svaki adapter je nezavisan: pad jednog ne rusi ostale (ok:false + razlog u JSON-u)."""
import json, os, sys, time, traceback
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ADAPTERS = os.path.join(HERE, "road_adapters")
OUT = os.path.join(HERE, "..", "data", "road_status.json")

COUNTRIES = {  # kod -> (ime, adapter fajl, izvor za prikaz)
    "SI": ("Slovenija", "si.py", "promet.si (DARS)"),
    "HR": ("Hrvatska", "hr.py", "HAK"),
    "RS": ("Srbija", "rs.py", "JP Putevi Srbije"),
    "BA": ("BiH", "ba.py", "BIHAMK"),
    "ME": ("Crna Gora", "me.py", "AMSCG"),
    "MK": ("S. Makedonija", "mk.py", "AMSM"),
    "AL": ("Albanija", "al.py", "ARRSH"),
    "BG": ("Bugarska", "bg.py", "MVR granična policija"),
    "RO": ("Rumunija", "ro.py", "CNAIR/CESTRIN"),
    "GR": ("Grčka", "gr.py", "Nea Odos / Aegean"),
}
METEO_COUNTRIES = ["RS", "HR", "SI", "BA", "ME", "MK", "BG", "RO", "GR"]  # AL nije clan Meteoalarma
MAX_ITEMS = 40

def run_adapter(path):
    """Exec adapter u izolovanom namespace-u i pozovi njegovu fetch* funkciju.

    0.9.95 (QA nalaz 93): vraca (stavke, nepotpuno). `nepotpuno` je spisak kategorija koje
    adapter NIJE uspeo da povuce, iako poziv nije bacio izuzetak - do sada je takav delimican
    pad zavrsavao kao `ok: true` i cela kategorija (npr. granicni prelazi) je nestajala bez
    traga. Adapter ga ostavlja u svom namespace-u pod imenom NEPOTPUNO."""
    ns = {"__name__": "adapter"}   # __main__ guard se ne pali
    with open(path, encoding="utf-8") as f:
        exec(compile(f.read(), path, "exec"), ns)
    def _pale():
        v = ns.get("NEPOTPUNO")
        return [str(x)[:60] for x in v] if isinstance(v, (list, tuple)) else []
    for name in ("fetch_items", "fetch_hak_items", "fetch_bihamk",
                 "fetch_mk_road_items", "fetch_bg_border_items", "fetch_greece_traffic", "fetch"):
        if callable(ns.get(name)):
            try:
                return ns[name](), _pale()
            except TypeError:
                break   # funkcija trazi argumente = pomocna, ne ulazna tacka (npr. ro.py fetch(url))
    if isinstance(ns.get("items"), list) and ns["items"]:  # top-level items lista (si.py, ro.py)
        return ns["items"], _pale()
    raise RuntimeError("adapter nema fetch funkciju ni items listu")

def izdvoj_granice(items, cc):
    """Granicni prelazi idu u poseban top-level kljuc, NE u items.
    Razlog: norm() secе listu na MAX_ITEMS, a granice su kod HAK-a poslednje u
    odgovoru (indeks 133+ od 143) pa su do sada UVEK bile odsecene. Uz to norm()
    spljosti stavku na 4 stringa i baci minute, smer i vreme ocitavanja."""
    gr = []
    for it in items:
        if not isinstance(it, dict) or not it.get("border"):
            continue
        b = it["border"]
        gr.append({
            "prelaz": str(it.get("title", ""))[:80],
            "zemlja": cc,
            "ulaz_auto": b.get("ulaz_auto"), "izlaz_auto": b.get("izlaz_auto"),
            "ulaz_teretno": b.get("ulaz_teretno"), "izlaz_teretno": b.get("izlaz_teretno"),
            "ocitano": b.get("ocitano"),          # vreme merenja PO CELIJI, ne po feedu
            "lat": b.get("lat"), "lon": b.get("lon"),
            "izvor": b.get("izvor"), "za": b.get("za", "putnicka vozila"),
        })
    return gr

def norm(items):
    """Vrati (stavke, koliko_je_odseceno).

    0.9.97 (QA nalaz 56): rez na MAX_ITEMS sece po redosledu fida, ne po vaznosti - zatvoren put
    ume tiho da ispadne, a kartica se predstavlja kao pun spisak. Broj odsecenih se od sada UPISUJE
    u fajl da bi moglo da se MERI koliko se stvarno gubi. Namerno se vozacu NE prikazuje (Boskova
    odluka ceka): posle sortiranja se gube samo radovi, nikad zatvaranja, a stotinak zapisa koje ne
    moze da poveze sa svojom rutom su sum.
    """
    out = []
    # granicni prelazi se izdvajaju posebno pa ne trose mesto u limitu
    obicni = [it for it in items if not (isinstance(it, dict) and it.get("border"))]
    odseceno = max(0, len(obicni) - MAX_ITEMS)
    for it in obicni[:MAX_ITEMS]:
        if not isinstance(it, dict):
            continue
        zap = {
            "type": str(it.get("type", "info"))[:40],
            "title": str(it.get("title", ""))[:160],
            "detail": str(it.get("detail", ""))[:300],
            "region": str(it.get("region", ""))[:80],
        }
        # GEOGRAFIJA (19.8.): do sada je norm() spljostavao svaku stavku na 4 stringa, pa je
        # aplikacija radove mogla da poredi SAMO po oznaci puta - a D8 je cela jadranska
        # magistrala, pa su radovi kod Opatije iskakali na ruti Murter-Sibenik. Izvor (HAK)
        # salje koordinatu za svaki dogadjaj; ovde je samo propustamo dalje.
        try:
            la, lo = it.get("lat"), it.get("lon")
            if la is not None and lo is not None:
                zap["lat"], zap["lon"] = round(float(la), 5), round(float(lo), 5)
        except (TypeError, ValueError):
            pass
        ln = it.get("coords")
        if isinstance(ln, list) and len(ln) >= 2:
            # deonica: [[lon,lat],...] - isti oblik kao deonice[].coords u stanje_puta.json.
            # Prorediemo na najvise 40 tacaka: dovoljno za "koliko je daleko od rute", a fajl
            # ostaje mali (robot ga osvezava 5x dnevno).
            korak = max(1, len(ln) // 40)
            tanko = []
            for p in ln[::korak]:
                try:
                    tanko.append([round(float(p[0]), 5), round(float(p[1]), 5)])
                except (TypeError, ValueError, IndexError):
                    pass
            if len(tanko) >= 2:
                zap["coords"] = tanko
        out.append(zap)
    return out, odseceno

def load_prev():
    """Prethodni rezultat - da pad jednog izvora ne obrise ono sto smo vec znali."""
    try:
        with open(OUT, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"countries": {}}

def main():
    prev = load_prev()
    now_iso = datetime.now(timezone.utc).isoformat(timespec="minutes")
    result = {"updated": now_iso, "countries": {}, "meteo": {}, "borders": []}
    fails = []
    for code, (name, fname, src) in COUNTRIES.items():
        entry = {"name": name, "source": src, "ok": False, "items": []}
        last_err = None
        for pokusaj in (1, 2, 3):   # izvori drzava umeju da budu spori iz tudje mreze
            try:
                sirovo, nepotpuno = run_adapter(os.path.join(ADAPTERS, fname))
                entry["items"], odseceno = norm(sirovo)
                if odseceno:
                    entry["odseceno"] = odseceno   # nalaz 56: merljivo u fajlu, nevidljivo vozacu
                result["borders"].extend(izdvoj_granice(sirovo, code))   # granice u poseban kljuc
                entry["ok"] = True
                entry["fetched"] = now_iso
                # 0.9.95 (nalaz 93): ok ostaje True (ostale kategorije JESU stigle), ali se
                # upisuje spisak onoga sto nije - inace app nema nacin ni da posteno cuti.
                if nepotpuno:
                    entry["nepotpuno"] = nepotpuno
                print(f"[OK ] {code} {name}: {len(entry['items'])} stavki"
                      + (f", NEPOTPUNO: {', '.join(nepotpuno)}" if nepotpuno else "")
                      + (f" (iz {pokusaj}. pokusaja)" if pokusaj > 1 else ""))
                break
            except Exception as e:
                last_err = e
                if pokusaj < 3:
                    time.sleep(4 * pokusaj)
        if not entry["ok"]:
            entry["error"] = str(last_err)[:200]
            fails.append(code)
            print(f"[FAIL] {code} {name}: {last_err}")
            # zadrzi poslednje poznato stanje umesto prazne liste, ali ga jasno oznaci
            p = (prev.get("countries") or {}).get(code) or {}
            if p.get("items"):
                entry["items"] = p["items"]
                entry["stale"] = True
                entry["fetched"] = p.get("fetched") or prev.get("updated")
                for g in (prev.get("borders") or []):   # granice iz poslednjeg poznatog stanja
                    if g.get("zemlja") == code:
                        result["borders"].append({**g, "stale": True})
                print(f"       zadrzano {len(entry['items'])} stavki od {entry['fetched']}")
        result["countries"][code] = entry
    # Meteoalarm - jedan adapter, po zemlji
    try:
        ns = {"__name__": "adapter"}
        with open(os.path.join(ADAPTERS, "meteo.py"), encoding="utf-8") as f:
            exec(compile(f.read(), "meteo.py", "exec"), ns)
        for cc in METEO_COUNTRIES:
            try:
                result["meteo"][cc] = norm(ns["fetch_meteoalarm"](cc))
                print(f"[OK ] meteo {cc}: {len(result['meteo'][cc])} upozorenja")
            except Exception as e:
                result["meteo"][cc] = []
                print(f"[FAIL] meteo {cc}: {e}")
    except Exception as e:
        print(f"[FAIL] meteoalarm modul: {e}")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(result, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    ok_c = sum(1 for c in result["countries"].values() if c["ok"])
    print(f"\nGOTOVO: {ok_c}/{len(COUNTRIES)} zemalja, meteo za {sum(1 for v in result['meteo'].values() if v is not None)} zemalja -> {os.path.normpath(OUT)}")
    if ok_c < 5:
        sys.exit(1)   # vecina pala = ne komituj polupraznu datoteku

main()
