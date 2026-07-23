import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# Meteoalarm (EUMETNET) legacy Atom feed - zvanicna meteo-upozorenja drzavnih zavoda.
# Isti URL obrazac: https://feeds.meteoalarm.org/feeds/meteoalarm-legacy-atom-<slug>
COUNTRY_SLUGS = {
    "RS": "serbia", "HR": "croatia", "SI": "slovenia", "BA": "bosnia-herzegovina",
    "ME": "montenegro", "MK": "republic-of-north-macedonia", "BG": "bulgaria",
    "RO": "romania", "GR": "greece", "HU": "hungary", "AT": "austria",
    # AL (Albanija) NIJE clan Meteoalarm-a - nema feed
}
ATOM = "{http://www.w3.org/2005/Atom}"
CAP = "{urn:oasis:names:tc:emergency:cap:1.2}"
LEVEL_SR = {"yellow": "zuto", "orange": "narandzasto", "red": "crveno"}


def fetch_meteoalarm(country_code="RS", only_active=True, timeout=20):
    """Vraca listu stavki {type,title,detail,region} za datu zemlju."""
    slug = COUNTRY_SLUGS[country_code.upper()]
    url = "https://feeds.meteoalarm.org/feeds/meteoalarm-legacy-atom-" + slug
    req = urllib.request.Request(url, headers={"User-Agent": "RouteMeRight/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        root = ET.fromstring(resp.read())

    now = datetime.now(timezone.utc)
    items = []
    for entry in root.findall(ATOM + "entry"):
        def txt(tag, ns=CAP):
            el = entry.find(ns + tag)
            return (el.text or "").strip() if el is not None and el.text else ""

        if txt("status") and txt("status") != "Actual":
            continue  # preskoci testove/vezbe
        expires = txt("expires")
        if only_active and expires:
            try:
                if datetime.fromisoformat(expires) < now:
                    continue  # vec isteklo
            except ValueError:
                pass
        # boja moze biti na pocetku ("Yellow thunderstorm warning" - HR)
        # ili na kraju ("Thunderstorm yellow" - RS) - trazi je bilo gde
        event = txt("event")
        title = txt("title", ATOM)
        m = re.search(r"\b(yellow|orange|red)\b", (event + " " + title).lower())
        level = LEVEL_SR.get(m.group(1)) if m else "?"
        phenomenon = re.sub(r"(?i)\b(yellow|orange|red|warning)\b", "", event).strip(" -") or event
        onset = txt("onset") or txt("effective")
        detail = "nivo: " + level + " | pojava: " + phenomenon
        if onset or expires:
            detail += " | vazi: " + onset[:16] + " do " + expires[:16]
        items.append({
            "type": "meteo-upozorenje",
            "title": title or event,
            "detail": detail,
            "region": txt("areaDesc") or country_code.upper(),
        })
    return items


if __name__ == "__main__":
    for it in fetch_meteoalarm("RS"):
        print(it)