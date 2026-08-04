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
    """Exec adapter u izolovanom namespace-u i pozovi njegovu fetch* funkciju."""
    ns = {"__name__": "adapter"}   # __main__ guard se ne pali
    with open(path, encoding="utf-8") as f:
        exec(compile(f.read(), path, "exec"), ns)
    for name in ("fetch_items", "fetch_hak_items", "fetch_bihamk",
                 "fetch_mk_road_items", "fetch_bg_border_items", "fetch_greece_traffic", "fetch"):
        if callable(ns.get(name)):
            try:
                return ns[name]()
            except TypeError:
                break   # funkcija trazi argumente = pomocna, ne ulazna tacka (npr. ro.py fetch(url))
    if isinstance(ns.get("items"), list) and ns["items"]:  # top-level items lista (si.py, ro.py)
        return ns["items"]
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
    out = []
    # granicni prelazi se izdvajaju posebno pa ne trose mesto u limitu
    obicni = [it for it in items if not (isinstance(it, dict) and it.get("border"))]
    for it in obicni[:MAX_ITEMS]:
        if not isinstance(it, dict):
            continue
        out.append({
            "type": str(it.get("type", "info"))[:40],
            "title": str(it.get("title", ""))[:160],
            "detail": str(it.get("detail", ""))[:300],
            "region": str(it.get("region", ""))[:80],
        })
    return out

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
                sirovo = run_adapter(os.path.join(ADAPTERS, fname))
                entry["items"] = norm(sirovo)
                result["borders"].extend(izdvoj_granice(sirovo, code))   # granice u poseban kljuc
                entry["ok"] = True
                entry["fetched"] = now_iso
                print(f"[OK ] {code} {name}: {len(entry['items'])} stavki"
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
