/* RouteMeRight - service worker.
   Zadatak: da aplikacija UOPSTE moze da se otvori bez signala. Bez ovoga ni sama ljuska
   (HTML, MapLibre, font) ne moze da se ucita, pa sacuvane rute nemaju gde da se prikazu.

   Pravila po vrsti sadrzaja:
   - LJUSKA (app, biblioteka, font, staticki podaci) = cache-first, osvezavanje u pozadini
   - PLOCICE MAPE = keširaju se SAMO one koje je korisnik stvarno gledao, uz gornju granicu.
     To nije skidanje regiona nego obicno pregledacko kesiranje; za pravi offline region
     dolazi PMTiles paket.
   - SERVISI (prognoza, rutiranje, POI) = nikad iz kesa. Bajata prognoza je gora od nikakve;
     kad nema mreze, aplikacija koristi ono sto je snimljeno uz sacuvanu rutu. */
const V = "rmr-v18";   /* v18: 0.9.85 presude 24.8. - kombinovana podrazumevana + svih 63 deonica u igri - nova ljuska mora da padne u telefon (24.8.). v17: 0.9.84 kurirano sivenje (kombinovana zna za dobre deonice iz baze zajednice) - nova ljuska mora da padne u telefon (24.8.). v16: 0.9.83 auto-pauza + pozadinski GPS most (fixKorak/rmrGpsPaket) - nova ljuska mora da padne u telefon (24.8.). v15: 0.9.82 runda 5 terenskih popravki (checkpoint voznje, nagib jedan izvor, snap trag, reroute paint-first, planner leak, ime cilja) - nova ljuska mora da padne u telefon (24.8.). v14: HUD identitet 0.9.79 - novo pismo (Saira Semi Condensed + JetBrains Mono) menja PRECACHE URL, pa stari kes koji jos drzi Archivo MORA da padne (16.8.). v13: test.html -> app.html; stari kes drzi staru ljusku pod starim imenom, MORA da padne (16.8.). v12: 0.9.78 altApply hibrid fix (16.8.). v11: 0.9.77 - pauza radar/prognoza, Druga ruta, tihe potvrde, pravne stranice (16.8.). v10: mesta_zajednice.json promenjeno (10 koordinata vraceno na prava mesta, 13.8.). v9: izbacen unos-pretpostavka. v7: preimenovani data fajlovi - stari kes mora da padne */
/* PAZNJA: v11 i v12 su nastali IZMENOM DIREKTNO U JAVNOM REPOU, ne ovde - zato je
   dev bio na v10 dok je produkcija bila na v12. tools/deploy.sh sada odbija deploy
   ako je javna verzija >= ove, da se kes nikad ne vrati unazad.
   NOTE: v11 and v12 were edited straight in the public repo, which is why dev sat on
   v10 while production ran v12. tools/deploy.sh now refuses to deploy if the public
   version is >= this one, so the cache can never move backwards. */
const LJUSKA = V + "-ljuska";
const PLOCICE = V + "-plocice";
const PLOCICA_MAX = 2500;

/* MapLibre i font MORAJU u precache: oni se ucitavaju iz <head>, dakle PRE nego sto
   service worker uopste postane aktivan, pa ih inace ne bi uhvatio ni na jednom otvaranju. */
const PRECACHE = [
  "./",
  "./app.html",
  "./data/bikes.json",
  "./data/prices.json",
  "./data/mesta_zajednice.json",
  "./data/pumpe.json",
  "./data/countries_bbox.json",
  "./data/manifest.webmanifest",
  "https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js",
  "https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css",
  "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700;800&family=Saira+Semi+Condensed:wght@400;600;700;800;900&display=swap",
  // Definicija stila i sprajtovi: i oni se traze pri pravljenju mape, dakle pre nego sto
  // service worker ozivi. Bez njih MapLibre bez signala ostaje zauvek na "Style is not done loading".
  "https://tiles.openfreemap.org/styles/positron",
  "https://tiles.openfreemap.org/planet",
  "https://tiles.openfreemap.org/sprites/ofm_f384/ofm.json",
  "https://tiles.openfreemap.org/sprites/ofm_f384/ofm.png",
  "https://tiles.openfreemap.org/sprites/ofm_f384/ofm@2x.json",
  "https://tiles.openfreemap.org/sprites/ofm_f384/ofm@2x.png",
];
const LJUSKA_HOST = /^(unpkg\.com|fonts\.googleapis\.com|fonts\.gstatic\.com)$/;
const PLOCICA_HOST = /^(tiles\.openfreemap\.org|.*\.basemaps\.cartocdn\.com|tilecache\.rainviewer\.com|s3\.amazonaws\.com|elevation-tiles-prod\.s3\.amazonaws\.com)$/;
const SERVIS_HOST = /(open-meteo\.com|met\.no|valhalla|overpass|nominatim|photon|router\.project-osrm\.org|supabase|rainviewer\.com\/public)/;

self.addEventListener("install", (e) => {
  e.waitUntil((async () => {
    const c = await caches.open(LJUSKA);
    await Promise.allSettled(PRECACHE.map((u) => c.add(new Request(u, { cache: "reload" }))));
    self.skipWaiting();
  })());
});

self.addEventListener("activate", (e) => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (!k.startsWith(V)) await caches.delete(k);
    await self.clients.claim();
  })());
});

async function ogranici(ime, max) {
  const c = await caches.open(ime);
  const k = await c.keys();
  for (let i = 0; i < k.length - max; i++) await c.delete(k[i]);   // najstarije prvo
}

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  let url;
  try { url = new URL(req.url); } catch { return; }
  if (url.protocol !== "http:" && url.protocol !== "https:") return;

  // servisi: uvek sa mreze, nikad iz kesa (bajata prognoza bi lagala)
  if (SERVIS_HOST.test(url.host) || SERVIS_HOST.test(url.href)) return;

  const istiKoren = url.origin === self.location.origin;

  // plocice mape: prvo kes (brzo i radi offline za vec gledane krajeve), pa mreza
  if (PLOCICA_HOST.test(url.host)) {
    e.respondWith((async () => {
      const c = await caches.open(PLOCICE);
      // caches.match gleda SVE kesove: definicija stila i sprajtovi su u precache-u (ljuska),
      // a plocice u svom kesu - bez ovoga se stil nikad ne nadje i mapa ostaje prazna
      const iz = (await c.match(req)) || (await caches.match(req));
      if (iz) return iz;
      try {
        const r = await fetch(req);
        if (r && r.ok) { c.put(req, r.clone()); ogranici(PLOCICE, PLOCICA_MAX); }
        return r;
      } catch (err) {
        return iz || Response.error();
      }
    })());
    return;
  }

  // APLIKACIJA I PODACI: mreza prvo, kes samo kao rezerva.
  // Podaci se menjaju (road_status se puni vise puta dnevno, stanje puta uz svaki uvoz), a
  // aplikacija ih trazi sa "?v=VERZIJA". Kes ih je nalazio preko ignoreSearch, pa je nova
  // verzija dobijala STARI fajl - tako je novi uvoz stigao na disk a u pregledacu se nije video.
  if (req.mode === "navigate" || (istiKoren && /\.(html|json)($|\?)/.test(url.pathname + url.search))) {
    e.respondWith((async () => {
      const c = await caches.open(LJUSKA);
      try {
        const r = await fetch(req);
        if (r && r.ok) c.put(req, r.clone());
        return r;
      } catch (err) {
        return (await c.match(req, { ignoreSearch: true })) ||
               (await c.match("./app.html", { ignoreSearch: true })) || Response.error();
      }
    })());
    return;
  }

  // ostatak ljuske: biblioteka, font, staticki podaci - kes prvo, osvezavanje u pozadini
  if (istiKoren || LJUSKA_HOST.test(url.host)) {
    e.respondWith((async () => {
      const c = await caches.open(LJUSKA);
      const iz = await c.match(req, { ignoreSearch: true });
      const sveze = fetch(req).then((r) => { if (r && r.ok) c.put(req, r.clone()); return r; }).catch(() => null);
      if (iz) { sveze; return iz; }
      const r = await sveze;
      return r || Response.error();
    })());
  }
});
