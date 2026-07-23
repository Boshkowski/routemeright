# Severna Makedonija - stanje na putevima (AMSM dnevne informacije)
# stdlib only: urllib.request, re, html
import urllib.request, re, html as h

URL = "https://amsm.mk/sostojba-na-patishta/dnevni-informacii/"

def _txt(s):
    s = re.sub(r"<[^>]+>", " ", s)
    s = h.unescape(s).replace("\xa0", " ").replace("﻿", "")
    return re.sub(r"\s+", " ", s).strip()

def fetch_mk_road_items():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    page = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")

    items = []

    # datum/vreme izvestaja: var roadConditionsPublished = "2026-07-23T00:00:00 | 12:00:00"
    m = re.search(r'roadConditionsPublished\s*=\s*"(\d{4}-\d{2}-\d{2})T[^"]*\|\s*(\d{2}:\d{2})', page)
    report_dt = (m.group(1) + " " + m.group(2)) if m else ""

    start = page.find("<strong>СОСТОЈБА")  # <strong>SOSTOJBA
    works_i = page.find("РАБОТИ НА ПАТ")  # RABOTI NA PAT
    end = page.find('class="mt-5 pt-3"', works_i)
    if end == -1:
        end = len(page)
    if start == -1 or works_i == -1:
        return items

    # 1) tekstualne sekcije (SOSTOJBA, FREKVENCIJA=granicni prelazi, upozorenja, zabrane...)
    seg = page[start:works_i]
    heads = [(mm.start(), mm.end(), _txt(mm.group(1)).rstrip(":"))
             for mm in re.finditer(r"<strong[^>]*>\s*([А-ШЃЅЈЉЊЌЏ][А-ШЃЅЈЉЊЌЏ2 ,:]{3,60}?)\s*:?(?:&nbsp;|\s)*</strong>", seg)]
    typemap = {"СОСТОЈБА": "sostojba",          # SOSTOJBA
               "ФРЕКВЕНЦИЈА": "granicni-prelazi",  # FREKVENCIJA
               "ВНИМАТЕЛНО": "upozorenje",  # VNIMATELNO
               "СЕЗОНСКИ": "rezim",             # SEZONSKI
               "ЗАБРАНА": "zabrana"}                 # ZABRANA
    for k, (hs, he, name) in enumerate(heads):
        body = seg[he:heads[k + 1][0] if k + 1 < len(heads) else len(seg)]
        detail = _txt(body).lstrip(": ")
        if not detail:
            continue
        typ = next((v for kk, v in typemap.items() if name.startswith(kk)), "info")
        region = "cela drzava"
        if typ == "granicni-prelazi":
            gps = re.findall(r"ГП\s+([А-ШЃЅЈЉЊЌЏ][а-шѓѕјљњќџ]+)", body)
            region = ", ".join("GP " + g for g in dict.fromkeys(gps)) or region
        title = name.title()
        if typ == "sostojba" and report_dt:
            title += " (" + report_dt + ")"
        items.append({"type": typ, "title": title, "detail": detail, "region": region})

    # 2) radovi na putu - <li> stavke posle "RABOTI NA PAT"
    for mm in re.finditer(r"<li[^>]*>(.*?)</li>", page[works_i:end], re.S):
        raw = mm.group(1)
        detail = _txt(raw)
        if len(detail) < 30:
            continue
        sm = re.search(r"<strong[^>]*>(.*?)</strong>", raw, re.S)
        region = _txt(sm.group(1)) if sm else ""
        items.append({"type": "radovi",
                      "title": (region or detail)[:60],
                      "detail": detail, "region": region})
    return items

if __name__ == "__main__":
    for it in fetch_mk_road_items():
        print(it["type"], "|", it["title"], "|", it["region"], "|", it["detail"][:90])