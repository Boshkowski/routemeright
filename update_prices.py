#!/usr/bin/env python3
"""Osvežava data/prices.json iz javnih izvora (best-effort, samo stdlib).

Pokretanje:  python3 update_prices.py
Ako izvor ne može da se pročita, stara vrednost OSTAJE i to se prijavi -
nikad ne upisujemo izmišljenu cifru.
"""
import json
import pathlib
import re
import sys
import urllib.request
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parent
PJ = ROOT / "data" / "prices.json"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "RouteMeRight-updater/1.0 (boskodjurica@gmail.com)"})
    return urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")


def num(s):
    """'196,00' -> 196.0 ; '2.78' -> 2.78"""
    s = s.strip()
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    return float(s)


def upd_rs(p, today):
    html = fetch("https://nafta.hr/sr/cene-goriva-srbija/")
    txt = re.sub(r"<[^>]+>", " ", html)
    m = re.search(r"BMB\s*95\s*Benzin[\s\S]{0,200}?(\d{3}[.,]\d{2})\s*RSD", txt, re.I)
    if not m:
        raise ValueError("BMB95 cena nije nađena u HTML-u")
    rsd = num(m.group(1))
    if not 120 <= rsd <= 350:
        raise ValueError(f"sumnjiva cena: {rsd} RSD")
    eur = round(rsd / p["meta"]["eurRsd"], 2)
    p["fuel"]["RS"].update({"eur": eur, "local": f"{rsd:.0f} RSD", "verified": today, "source": "nafta.hr (auto)"})
    return f"RS benzin: {rsd:.0f} RSD = {eur} EUR/L"


def upd_ba(p, today):
    html = fetch("https://nafta.hr/sr/cene-goriva-bosna/")
    txt = re.sub(r"<[^>]+>", " ", html)
    m = re.search(r"BMB\s*95\D{0,30}?(\d[.,]\d{2})\s*KM", txt, re.I)
    if not m:
        raise ValueError("BMB95 KM cena nije nađena")
    km = num(m.group(1))
    if not 1.5 <= km <= 5:
        raise ValueError(f"sumnjiva cena: {km} KM")
    eur = round(km / p["meta"]["eurBam"], 2)
    p["fuel"]["BA"].update({"eur": eur, "local": f"{km:.2f} KM", "verified": today, "source": "nafta.hr (auto)"})
    return f"BA benzin: {km:.2f} KM = {eur} EUR/L"


def upd_me(p, today):
    html = fetch("https://nafta.hr/sr/cene-goriva-crna-gora/")
    m = re.search(r"BMB[\s-]*95.{0,300}?(\d[.,]\d{2})\s*€", html, re.S | re.I)
    if not m:
        raise ValueError("BMB95 EUR cena nije nađena")
    eur = num(m.group(1))
    if not 0.9 <= eur <= 2.5:
        raise ValueError(f"sumnjiva cena: {eur} EUR")
    p["fuel"]["ME"].update({"eur": round(eur, 2), "verified": today, "source": "nafta.hr (auto)"})
    return f"ME benzin: {eur} EUR/L"


def upd_hr(p, today):
    html = fetch("https://www.hak.hr/info/cijene-goriva/")
    # HAK lista min/max/medijan - tražimo medijan za Eurosuper 95
    m = re.search(r"Eurosuper\s*95[\s\S]{0,600}?(\d[.,]\d{2})[\s\S]{0,80}?(\d[.,]\d{2})[\s\S]{0,80}?(\d[.,]\d{2})", html, re.I)
    if not m:
        raise ValueError("Eurosuper 95 nije nađen")
    vals = sorted(num(g) for g in m.groups())
    eur = vals[1]  # srednja od tri = medijan
    if not 0.9 <= eur <= 2.5:
        raise ValueError(f"sumnjiva cena: {eur} EUR")
    p["fuel"]["HR"].update({"eur": round(eur, 2), "verified": today, "source": "HAK medijan (auto)"})
    return f"HR benzin: {eur} EUR/L (medijan)"


def upd_tolls(p, today):
    """Auto-VERIFIKACIJA putarina i vinjeta: potvrdi da zvanicni izvor i dalje
    prikazuje cenu koju imamo. Na poklapanje -> verified=danas. Na promenu ->
    NE menja cifru sam, nego upise note za rucnu proveru (cena je pravna stvar)."""
    out = []
    checks = [
        ("vignette", "SI", "https://www.tolls.eu/slovenia", r"8[.,]00"),
        ("vignette", "AT", "https://www.asfinag.at/maut-vignette/vignette/", r"5[.,]10"),
        ("vignette", "HU", "https://www.tolls.eu/hungary", [r"[Mm]otorcycle", r"5[\s.]?550"]),
        ("tollMotoPerKm", "RS", "https://www.tolls.eu/serbia", r"1[\s.]?030"),
        ("tollMotoPerKm", "HR", "https://www.tolls.eu/croatia", r"10[.,]8"),
    ]
    done = set()
    for sect, cc, url, pat in checks:
        key = sect + cc
        if key in done:
            continue
        try:
            html = fetch(url)
            txt = re.sub(r"<[^>]+>", " ", html)
            pats = pat if isinstance(pat, list) else [pat]
            if all(re.search(x, txt) for x in pats):
                p[sect][cc]["verified"] = today
                p[sect][cc].pop("note", None)
                out.append(f"{cc} {sect}: potvrdjeno ({pat})")
                done.add(key)
            else:
                p[sect][cc]["note"] = f"PROVERI RUCNO: {pat} nije nadjen na {url} ({today})"
                out.append(f"{cc} {sect}: NIJE potvrdjeno na {url}")
        except Exception as e:
            out.append(f"{cc} {sect}: izvor nedostupan ({e})")
    return "; ".join(out)


def main():
    p = json.loads(PJ.read_text(encoding="utf-8"))
    today = date.today().isoformat()
    ok, fail = [], []
    for name, fn in [("RS", upd_rs), ("BA", upd_ba), ("ME", upd_me), ("HR", upd_hr), ("TOLLS", upd_tolls)]:
        try:
            ok.append(fn(p, today))
        except Exception as e:
            fail.append(f"{name}: {e} (stara vrednost zadržana)")
    if ok:
        p["meta"]["updated"] = today
        PJ.write_text(json.dumps(p, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Ažurirano:" if ok else "Ništa nije ažurirano.")
    for line in ok:
        print("  +", line)
    for line in fail:
        print("  !", line)
    # putarine/vinjete se menjaju retko - proveravaju se ručno (izvori su u prices.json)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
