import urllib.request, re, html as H

UA = {'User-Agent': 'Mozilla/5.0 (RouteMeRight)'}

def fetch(url, enc='utf-8'):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=30).read().decode(enc, 'replace')

def clean(x):
    return re.sub(r'\s+', ' ', H.unescape(re.sub(r'<[^>]+>', ' ', x))).strip()

items = []

# 1) CNAIR/CESTRIN - privremene restrikcije (radovi, suzenja, zatvaranja) po DN/A putevima
try:
    idx = fetch('https://www.cestrin.ro/restrictii/')
    rel = re.search(r'href="([^"]*Centralizator/Temporare/[^"]+\.htm)"', idx).group(1)
    page = fetch('https://www.cestrin.ro/restrictii/' + rel, 'windows-1252')
    for row in re.findall(r'<tr[^>]*>(.*?)</tr>', page, re.S):
        c = [clean(x) for x in re.findall(r'<td[^>]*>(.*?)</td>', row, re.S)]
        if len(c) >= 14 and c[0].isdigit() and c[1] in ('DN', 'A', 'DX') and c[2]:
            road = c[2] if c[2].upper().startswith(c[1].upper()) else c[1] + c[2]
            cause = ' '.join(filter(None, [c[12], c[13]])) or 'restrictie'
            if re.search(r'inchis|închis', cause, re.I):
                typ = 'zatvaranje'
            elif re.search(r'lucr|execu|marcaj|repara|antier', cause, re.I):
                typ = 'radovi'
            else:
                typ = 'restrikcija'
            items.append({
                'type': typ,
                'title': '%s: %s' % (road, cause),
                'detail': 'km %s+%s do %s+%s, %s' % (c[3], c[5], c[7], c[9], c[10]),
                'region': c[11]})
except Exception as e:
    print('CESTRIN fail:', e)

# 2) Granicni prelazi - prosecno cekanje uzivo (Politia de Frontiera; default auta/ulaz, ?vt=2 kamioni, ?dt=2 izlaz)
try:
    b = fetch('https://www.politiadefrontiera.ro/ro/traficonline/?vw=2')
    for row in re.findall(r'<tr[^>]*>(.*?)</tr>', b, re.S):
        name = re.search(r'class="pointtitle"[^>]*>([^<]+)', row)
        if not name:
            continue
        wait = re.search(r'Timp de a.?teptare\s*(\d+)\s*min', row)
        info = re.search(r'</td>\s*<td>([^<]{3,})</td>', row)
        items.append({
            'type': 'granicni_prelaz',
            'title': clean(name.group(1)),
            'detail': ('cekanje %s min' % wait.group(1) if wait else 'n/a') +
                      ('; ' + clean(info.group(1)) if info else ''),
            'region': 'granica RO'})
except Exception as e:
    print('PFR fail:', e)

for it in items[:8]:
    print(it)
print('TOTAL:', len(items))