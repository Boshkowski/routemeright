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
const V = "rmr-v35";   /* v35: 0.9.106 - preostalo vreme u voznji, Atlas izlog se ne zaglavljuje, Uvezi GPX u traci Atlasa. v34: 0.9.105 - dijalozi ostavljaju trajan trag (mr_dijalog) i ulaze u izvoz. v33: 0.9.104 - pretraga po imenu (bravar vise nije prvi red), Enter ne bira kad je vrh neresen, polja OD/DO kroz isti lanac. v32: 0.9.103 - teren 27.8.: provera verzije (nova ljuska MORA da padne u telefon), nagib posle pauze, sazetak ne pojede meni, Breza 10, koridori kroz terenske ocene, X u oblacicu i replayu. v31: 0.9.102 - svih 11 odobrenih nalaza (13, 34, 35, 37, 38, 78, 88, 95, 96, 97, 106). v30: 0.9.101 - politika privatnosti nabraja umesto da broji (nalaz 61); privatnost.html NIJE u PRECACHE pa nov tekst stize pri prvom otvaranju sa signalom. v29: 0.9.100 - Boskove odluke o pauzi (105c, 73, 75): izlaz priznaje odmak od 150 m, rucna pauza se gasi sama posle 2 min istrajne voznje i to kaze, stajanje od 3 min ostaje u dnevniku. v28: 0.9.99 - dve regresije iz 0.9.98 uhvacene pre voznje (histereza opoziva dolaska; poruka "nemam uputstva" vise ne gazi "Van rute"). v27: 0.9.98 - runda iskrenosti (nalazi 11, 26, 27, 39, 54, 56, 62, 69, 83, 94, 103): app prestaje da tvrdi ono sto nema cime da potkrepi i da cuti o onome sto je uradio. Plocice i teren OSTAJU - njihova imena vise ne nose V. v26: 0.9.97 - plocice i teren vise NE nose verziju u imenu kesa (nalaz 85: svaki apdejt je brisao mapu, pa je prva voznja bez signala bila bez podloge) + pozadinski paket ne laze nativni sloj (nalaz 99). OVAJ activate JOS JEDNOM brise stari rmr-v25-plocice - ime nosi verziju, drugacije se ne moze - i to je POSLEDNJI put. v25: 0.9.96 - rupe u tragu se broje i javljaju (QA nalaz 100); nova ljuska MORA da padne u telefon. v24: 0.9.95 - kljuc kesa vise ne nosi upit (bez signala se servirala NAJSTARIJA kopija svakog podatka, QA nalaz 53) + noc popravki 27.8.; nova ljuska MORA da padne u telefon. v23: 0.9.90 Atlas deonica (rezim nad mapom iz taba Rute: sve deonice u jednoj boji, kartica sa ocenama zajednice, "Vodi me preko nje") - nova ljuska mora da padne u telefon (25.8.). v22: 0.9.89 ocene deonica (kartica u sazetku + mr_ocene overlay + prijave kanal bez koordinata) - nova ljuska mora da padne u telefon (25.8.). v21: 0.9.88 mini-runda presuda (drugi slot za pecene, mr_defRuta, "Vozi i ti" link, Povezi voznje u turu) - nova ljuska mora da padne u telefon (25.8.). v20: 0.9.87 pecena baza kuriranih deonica (unija za sivenje u loadPutevi) - nova ljuska mora da padne u telefon (25.8.). v19: 0.9.86 zaokruzi turu - ture sa etapama, dnevnik cap 30 - nova ljuska mora da padne u telefon (25.8.). v18: 0.9.85 presude 24.8. - kombinovana podrazumevana + svih 63 deonica u igri - nova ljuska mora da padne u telefon (24.8.). v17: 0.9.84 kurirano sivenje (kombinovana zna za dobre deonice iz baze zajednice) - nova ljuska mora da padne u telefon (24.8.). v16: 0.9.83 auto-pauza + pozadinski GPS most (fixKorak/rmrGpsPaket) - nova ljuska mora da padne u telefon (24.8.). v15: 0.9.82 runda 5 terenskih popravki (checkpoint voznje, nagib jedan izvor, snap trag, reroute paint-first, planner leak, ime cilja) - nova ljuska mora da padne u telefon (24.8.). v14: HUD identitet 0.9.79 - novo pismo (Saira Semi Condensed + JetBrains Mono) menja PRECACHE URL, pa stari kes koji jos drzi Archivo MORA da padne (16.8.). v13: test.html -> app.html; stari kes drzi staru ljusku pod starim imenom, MORA da padne (16.8.). v12: 0.9.78 altApply hibrid fix (16.8.). v11: 0.9.77 - pauza radar/prognoza, Druga ruta, tihe potvrde, pravne stranice (16.8.). v10: mesta_zajednice.json promenjeno (10 koordinata vraceno na prava mesta, 13.8.). v9: izbacen unos-pretpostavka. v7: preimenovani data fajlovi - stari kes mora da padne */
/* PAZNJA: v11 i v12 su nastali IZMENOM DIREKTNO U JAVNOM REPOU, ne ovde - zato je
   dev bio na v10 dok je produkcija bila na v12. tools/deploy.sh sada odbija deploy
   ako je javna verzija >= ove, da se kes nikad ne vrati unazad.
   NOTE: v11 and v12 were edited straight in the public repo, which is why dev sat on
   v10 while production ran v12. tools/deploy.sh now refuses to deploy if the public
   version is >= this one, so the cache can never move backwards. */
const LJUSKA = V + "-ljuska";
/* 0.9.96 (QA nalaz 85): ime kesa plocica je nosilo VERZIJU, pa je svako podizanje ljuske brisalo
   sve plocice - a plocice nemaju nikakve veze sa verzijom aplikacije, adresirane su po z/x/y.
   Posledica: prva voznja bez signala posle svakog apdejta = obojena podloga bez puteva i imena,
   bas ono zbog cega app na putu i postoji. Sada im ime ne nosi V i activate ih preskace.

   DEM (teren) dobija SVOJ kes sa malim plafonom, jer je izmereno 27.8. na zivim izvorima:
   podloga z12 ~40 KB, DEM terrarium z12 ~106 KB, z10 ~136 KB - dakle 2,5x do 3,4x veci, a
   3D senka brda je ukras: bez signala vozacu treba PUT. Plafoni drze ukupan kes oko 115 MB
   (2000 x 40 KB + 300 x 120 KB). To je bitno jer iOS kvotu origina resava izbacivanjem CELOG
   skladista sajta - a tu zive i IndexedDB paketi sacuvanih ruta. */
const PLOCICE = "rmr-plocice";
const DEM = "rmr-dem";
const PLOCICA_MAX = 2000;   // ~80 MB podloge = ceo Balkan na z12
const DEM_MAX = 300;        // ~36 MB terena

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
const PLOCICA_HOST = /^(tiles\.openfreemap\.org|.*\.basemaps\.cartocdn\.com|s3\.amazonaws\.com|elevation-tiles-prod\.s3\.amazonaws\.com)$/;
const DEM_HOST = /^(elevation-tiles-prod\.s3\.amazonaws\.com|s3\.amazonaws\.com)$/;
/* Radar je izbacen iz kesa plocica (nalaz 85): okvir nosi vremensku oznaku u URL-u, pa se
   NIKAD ne trazi drugi put - samo je punio kes i po FIFO pravilu izbacivao podlogu koja
   vozacu stvarno treba. Uz to je ziv podatak, tacno ono sto ovaj fajl zove "servis".
   Grana servisa se testira PRE grane plocica, pa siri obrazac stvarno odvodi radar odavde. */
const SERVIS_HOST = /(open-meteo\.com|met\.no|valhalla|overpass|nominatim|photon|router\.project-osrm\.org|supabase|rainviewer\.com)/;

self.addEventListener("install", (e) => {
  e.waitUntil((async () => {
    const c = await caches.open(LJUSKA);
    await Promise.allSettled(PRECACHE.map((u) => c.add(new Request(u, { cache: "reload" }))));
    self.skipWaiting();
  })());
});

self.addEventListener("activate", (e) => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k !== PLOCICE && k !== DEM && !k.startsWith(V)) await caches.delete(k);   // nalaz 85: plocice i teren prezivljavaju apdejt
    await self.clients.claim();
  })());
});

/* 0.9.95 (QA nalaz 92): rez NIKAD ne sme da pojede PRECACHE. `ogranici` brise najstarije unose
   prvo, a najstariji unosi u ljusci su tacno app.html, MapLibre, font i definicija stila - dakle
   bas ono zbog cega ljuska i postoji. Zato cuvaj-lista. Najveci deo rasta je ionako nestao sa
   kljucem bez upita (nalaz 53): jedan fajl = jedan unos. */
const CUVAJ = new Set(PRECACHE.map((u) => new URL(u, self.location).href));
const LJUSKA_MAX = 80;   // van precache-a: app data + sve sto runtime dovuce; jedan unos po fajlu (kljuc bez upita)
async function ogranici(ime, max, cuvaj) {
  const c = await caches.open(ime);
  const k = await c.keys();
  const rez = cuvaj ? k.filter((r) => !cuvaj.has(r.url)) : k;
  for (let i = 0; i < rez.length - max; i++) await c.delete(rez[i]);   // najstarije prvo, precache netaknut
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
      const jeDem = DEM_HOST.test(url.host);
      const kesIme = jeDem ? DEM : PLOCICE;
      const kesMax = jeDem ? DEM_MAX : PLOCICA_MAX;
      const c = await caches.open(kesIme);
      // caches.match gleda SVE kesove: definicija stila i sprajtovi su u precache-u (ljuska),
      // a plocice u svom kesu - bez ovoga se stil nikad ne nadje i mapa ostaje prazna
      const iz = (await c.match(req)) || (await caches.match(req));
      if (iz) return iz;
      try {
        const r = await fetch(req);
        if (r && r.ok) { c.put(req, r.clone()); ogranici(kesIme, kesMax); }
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
      /* 0.9.95 (QA nalaz 53): kesiralo se pod PUNIM URL-om sa upitom, a app namerno menja upit na
         osam mesta (satni kljuc za road_status, dnevni za prices, verzija+datum za mesta
         zajednice...). U kesu je zato stajalo VISE kopija istog fajla, a rezerva `ignoreSearch`
         po specifikaciji vraca PRVI unos po redosledu ubacivanja - dakle NAJSTARIJI. Bez signala
         se tako servirala najstarija kopija svakog podatka. Kljuc je sada bez upita: jedan fajl,
         jedan unos, i uvek poslednji uspesno preuzet. */
      const kljuc = url.origin + url.pathname;
      try {
        const r = await fetch(req);
        if (r && r.ok) { await c.put(new Request(kljuc), r.clone()); ogranici(LJUSKA, LJUSKA_MAX, CUVAJ); }   // 0.9.95 (nalaz 92): rez koji NE dira precache
        return r;
      } catch (err) {
        return (await c.match(kljuc)) ||
               (await c.match(req, { ignoreSearch: true })) ||
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
