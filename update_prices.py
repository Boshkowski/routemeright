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
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "hr,sr;q=0.8,en;q=0.6",
    })   # nafta.hr GitHub runnerima (cloud IP) na bot-UA vraca drugaciji HTML - browser zaglavlja pomazu (6.8.)
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


def upd_eu(p, today):
    """EU Weekly Oil Bulletin (zvanicni EC izvor, svih 27 zemalja odjednom, cene VEC u EUR/1000 l).
    GUID dokumenta je STABILAN - EC svakog ponedeljka zameni sadrzaj istim linkom (provereno 6.8.2026).
    xlsx se parsira stdlib-om (zip + XML regex) - bez ijedne zavisnosti."""
    import zipfile, io
    from datetime import date as _d, timedelta
    url = "https://energy.ec.europa.eu/document/download/264c2d0f-f161-4ea3-a777-78faae59bea0_en"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15"})
    raw = urllib.request.urlopen(req, timeout=40).read()
    z = zipfile.ZipFile(io.BytesIO(raw))
    ss = [re.sub(r"<[^>]+>", "", s) for s in re.findall(r"<si>(.*?)</si>", z.read("xl/sharedStrings.xml").decode(), re.S)]
    xml = z.read("xl/worksheets/sheet1.xml").decode()
    serial = None
    EU_CC = {"Austria": "AT", "Bulgaria": "BG", "Germany": "DE", "Greece": "GR",
             "Hungary": "HU", "Italy": "IT", "Romania": "RO", "Slovenia": "SI"}   # HR ide preko HAK-a (svezije od ponedeljackog biltena)
    got = []
    for rxml in re.findall(r"<row[^>]*>(.*?)</row>", xml, re.S):
        cells = {}
        for c in re.finditer(r'<c r="([A-Z]+)\d+"(?:[^>]*t="(\w+)")?[^>]*>(?:<v>([^<]*)</v>)?', rxml):
            if c.group(3) is None:
                continue
            cells[c.group(1)] = ss[int(c.group(3))] if c.group(2) == "s" else c.group(3)
        a, b = cells.get("A"), cells.get("B")
        if a and serial is None and re.fullmatch(r"\d{5}(\.0*)?", a):
            serial = int(float(a))   # Excel serijski datum nedelje biltena
            if (_d.today() - _d(1899, 12, 30) - timedelta(days=serial)).days > 21:
                wob = (_d(1899, 12, 30) + timedelta(days=serial)).isoformat()
                raise ValueError(f"bilten je ustajao ({wob}) - nista nije upisano")   # PRE upisa ijedne vrednosti
        if a in EU_CC and b:
            cc = EU_CC[a]
            try:
                eur = float(b) / 1000.0   # EUR po 1000 l -> EUR/L
            except ValueError:
                continue
            if not 0.9 <= eur <= 3.2:
                continue   # sumnjiva cifra se NE upisuje (ne odokativno)
            if cc in p["fuel"]:
                p["fuel"][cc].update({"eur": round(eur, 2), "verified": today, "source": "EU Weekly Oil Bulletin (auto)"})
                got.append(f"{cc} {eur:.2f}")
    if not got:
        raise ValueError("nijedna zemlja nije parsirana iz biltena")
    wob_date = (_d(1899, 12, 30) + timedelta(days=serial)).isoformat() if serial else "?"
    return f"EU bilten ({wob_date}): " + " · ".join(got)


def main():
    p = json.loads(PJ.read_text(encoding="utf-8"))
    today = date.today().isoformat()
    ok, fail = [], []
    for name, fn in [("RS", upd_rs), ("BA", upd_ba), ("ME", upd_me), ("HR", upd_hr), ("EU", upd_eu)]:
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
