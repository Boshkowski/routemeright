import urllib.request, xml.etree.ElementTree as ET, re, json, socket, html

FEED = "https://www.arrsh.gov.al/informacion-i-gjendjeve-te-rrugeve.html/feed"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"}

# Neki lokalni DNS-ovi povremeno SERVFAIL-uju za .gov.al -> fallback: DoH (dns.google), pa hardkodovan IP
_orig_gai = socket.getaddrinfo
def _gai(host, *a, **kw):
    try:
        return _orig_gai(host, *a, **kw)
    except socket.gaierror:
        if "arrsh.gov.al" in str(host):
            ip = "134.0.41.206"
            try:
                q = urllib.request.Request("https://dns.google/resolve?name=%s&type=A" % host, headers=UA)
                ans = json.load(urllib.request.urlopen(q, timeout=10)).get("Answer", [])
                ips = [r["data"] for r in ans if r.get("type") == 1]
                if ips: ip = ips[0]
            except Exception:
                pass
            return _orig_gai(ip, *a, **kw)
        raise
socket.getaddrinfo = _gai

def _clean(s):
    s = re.sub(r"(?s)<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", html.unescape(s)).strip()

def _classify(txt):
    t = txt.lower()
    if re.search(r"mbyll|pezull|bllok|devij|nderpr|ndërpr|kufizim", t): return "closure"
    if re.search(r"punime|ndertim|ndërtim|rehabilit|rikonstruk|zgjerim|asfalt|inspektim|kantier", t): return "roadwork"
    if re.search(r"reshje|bora|dëbor|debor|akull|mot i keq|rrëshqitje|rreshqitje", t): return "weather"
    return "info"

def _region(txt):
    m = re.search(r"[A-ZÇË][a-zçë]+(?:[ëe]s)?(?:\s*[–\-]\s*[A-ZÇË][a-zçë]+){1,3}", txt)
    if m: return m.group(0)
    m = re.search(r"(?:rrug[eë]s?\s+(?:s[eë]\s+)?|Bypass-?it?\s+t[eë]\s+|n[eë]\s+)([A-ZÇË][a-zçë]{3,})", txt)
    return m.group(1) if m else "Shqiperi"

def fetch_items():
    req = urllib.request.Request(FEED, headers=UA)
    root = ET.fromstring(urllib.request.urlopen(req, timeout=30).read())
    items = []
    for it in root.iter("item"):
        title = _clean(it.findtext("title"))
        desc = _clean(it.findtext("description"))
        date = (it.findtext("pubDate") or "").strip()
        link = (it.findtext("link") or "").strip()
        detail = (desc[:300] + (" | " + date if date else "") + (" | " + link if link else "")).strip(" |")
        items.append({
            "type": _classify(title + " " + desc),
            "title": title,
            "detail": detail,
            "region": _region(title + " " + desc),
        })
    return items

if __name__ == "__main__":
    for x in fetch_items():
        print(json.dumps(x, ensure_ascii=False))