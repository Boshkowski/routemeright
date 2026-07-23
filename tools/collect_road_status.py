#!/usr/bin/env python3
"""Sakuplja stanje na putevima (10 zemalja) + Meteoalarm upozorenja -> data/road_status.json.
Pokrece ga GitHub Action (.github/workflows/road-status.yml) 5x dnevno.
Adapteri u tools/road_adapters/ su testirani uzivo 2026-07-23 (multi-agent provera).
Svaki adapter je nezavisan: pad jednog ne rusi ostale (ok:false + razlog u JSON-u)."""
import json, os, sys, traceback
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

def norm(items):
    out = []
    for it in items[:MAX_ITEMS]:
        if not isinstance(it, dict):
            continue
        out.append({
            "type": str(it.get("type", "info"))[:40],
            "title": str(it.get("title", ""))[:160],
            "detail": str(it.get("detail", ""))[:300],
            "region": str(it.get("region", ""))[:80],
        })
    return out

def main():
    result = {"updated": datetime.now(timezone.utc).isoformat(timespec="minutes"),
              "countries": {}, "meteo": {}}
    fails = []
    for code, (name, fname, src) in COUNTRIES.items():
        entry = {"name": name, "source": src, "ok": False, "items": []}
        try:
            entry["items"] = norm(run_adapter(os.path.join(ADAPTERS, fname)))
            entry["ok"] = True
            print(f"[OK ] {code} {name}: {len(entry['items'])} stavki")
        except Exception as e:
            entry["error"] = str(e)[:200]
            fails.append(code)
            print(f"[FAIL] {code} {name}: {e}")
            traceback.print_exc()
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
