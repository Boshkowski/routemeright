import urllib.request, re

URL = "https://www.putevi-srbije.rs/stanje/novamapa/textfile.txt"  # latinica; textfile_cir.txt = cirilica

TYPE_MAP = {"RADOVI": "roadworks", "OBUSTAVE": "closure", "ZABRANE": "restriction", "ODRONI": "landslide"}

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
        items.append({"type": typ, "title": rest.strip(), "detail": detail, "region": region})
    return items

if __name__ == "__main__":
    for it in fetch_items():
        print(it)