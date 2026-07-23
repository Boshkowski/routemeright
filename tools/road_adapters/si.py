import urllib.request, xml.etree.ElementTree as ET

URL = "https://www.promet.si/dc/b2b.dogodki.rss"  # dodaj ?language=en_US za engleski
NS = {"a": "http://www.w3.org/2005/Atom"}

req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (RouteMeRight)"})
with urllib.request.urlopen(req, timeout=30) as r:
    root = ET.fromstring(r.read())

items = []
for e in root.findall("a:entry", NS):
    title = (e.findtext("a:title", "", NS) or "").strip()
    cat = e.find("a:category", NS)
    typ = cat.get("term") if cat is not None else ""
    detail = (e.findtext("a:summary", "", NS) or "").strip()
    # region = deo naslova pre ":" -> put + deonica, npr. "A1-E57, Ljubljana - Maribor"
    region = title.split(":")[0].strip() if ":" in title else ""
    items.append({"type": typ, "title": title, "detail": detail, "region": region})

print(len(items), "stavki")
for it in items[:5]:
    print(it)