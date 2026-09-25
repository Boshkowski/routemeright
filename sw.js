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
const V = "rmr-v87";   /* v87: 0.9.158 - sezona prevoja (data/prelazi.json je NOV fajl u PRECACHE, kes mora da padne da bi ga dobio). v86: 0.9.157 - 29 novih tura (GR/SI/RO/BG), spisak sa 76 na 105; app.html je veci pa kes mora da padne. v85: 0.9.156 - 3D reljef vracen sa osiguracem i prekidacem u Slojevima; jedan izvor visina umesto dva. v84: 0.9.155 - vraceni prelazi i animacije, vracena popravljena uvodna animacija; teren ostaje iskljucen. v83: 0.9.154 - iskljucen 3D teren (mrtva render petlja = mrtav gest) + cuvar koji ozivi iscrtavanje. v82: 0.9.153 - broji dodir kroz cetiri faze (dokument, kontejner hvatanje/mehur, prozor) i cita rukovaoce gestovima iz mape. v81: 0.9.152 - brojaci se kace tek kad mapa postoji (bile su lazne nule) + samoprovera koja pomera mapu iz koda. v80: 0.9.151 - merenje otkucaja ekrana i WebGL konteksta + preuzimanje dogadjaja o gubitku konteksta (mapa nije iscrtavala kadrove). v79: 0.9.150 - panel broji MapLibre dogadjaje i belezi greske stranice (dodir stize do mape a kamera se ne mice). v78: 0.9.149 - vracena funkcija dodirStanje (spisak novosti se nije otvarao), animacije takodje privremeno skracene. v77: 0.9.148 - svi prelazi privremeno skraceni na .01ms (kvar je u prelazima, ne u dodiru). v76: 0.9.147 - merni panel (dodiri i stanje mape) na vrhu spiska novosti. v75: 0.9.146 - web sloj vracen tacno na 0.9.141 (mapa je prestala da prima prst posle 0.9.142). v74: 0.9.145 - touch-action: none na mapi (prst je mapin, ne skrol stranice) + merni panel na vrhu spiska novosti. v73: 0.9.144 - uvodni sloj ne prima dodir i izbacuje se iz dokumenta; dnevnik dodira u spisku novosti. v72: 0.9.143 - ikona aplikacije ima narandzasto krilo (Boskov izbor A, 17.9.) - iste putanje, nove bajte, pa kes MORA da padne da bi se videla nova ikona. v71: 0.9.142 - uvodna animacija izuzeta iz globalnog reseta za "smanji kretanje" (gasila se u prvom kadru), pokret krece od prvog stvarnog kadra, dnevnik uvoda u spisku novosti. v70: ispravljen datum izdanja 0.9.140 i 0.9.141 u spisku novosti (bio 17.09., a napravljeni su 16.09.). v69: 0.9.141 - kompas vraca sever (bio prekriven), jedna sirina pisma, traka snimka skupljena, uvodna animacija od prvog kadra. v68: 0.9.140 - red za izbor liste u Istrazi prebacen sa pilula na Filipove kartice sa crtom. v67: 0.9.139 - izbor isecka na traci replaya; traka izbora u pravoj osi; granice se ciste. v66: 0.9.138 - GPX ima dom: peti cip "Moje rute"; uvezena ruta se cuva. v65: 0.9.137 - Ture su kolekcije sa naslovima (podela, ne preklapanje). v64: 0.9.136 - Mesta u pojasevima po blizini, sa vrstom i istim prstenom kao "Blizu tebe". v63: 0.9.135 - "Blizu tebe" je prsten nad DEONICAMA (ne vise nad 76 tura), krug na mapi, put do kruzne ture. v62: 0.9.134 - filteri Istrazi: jedno dugme i jedan list sa segmentiranim trakama umesto pet redova cipova. v61: 0.9.133 - traka Istrazi: visina je jedini izvor istine, jedan potez ide do kraja, prevlaci se i zaglavlje. v60: 0.9.132 - sazetak: "Detalji voznje" kao red koji se otvara na mestu, plafon od 5 stavki pao, upozorenja ulaze. v59: 0.9.131 - ozivljen mrtav blok: uvoz GPX-a, "Vodi me" u Mestima i pilula rute ponovo rade; kruzna tura na jedno mesto; poruke u red umesto prepisivanja. v58: 0.9.130 - deljena slika se cuva i u galeriju telefona (nativni most RmrGalerija, zamerka 12 izbor C). v57: 0.9.129 - dugme za fotografiju je red ispod pregleda (Boskova zamerka 11, izbor B); blok "03 / Fotografija" uklonjen. v56: 0.9.128 - ekran za deljenje na tokenima aplikacije (Atlas paleta umesto hladne). v55: 0.9.127 - uvodna animacija znaka umesto crnog ekrana pri paljenju. v54: 0.9.126 - tab Istrazi (maketa C): mapa je pocetno stanje, jedna traka sa cetiri liste, fiksna traka Atlasa uklonjena. v53: 0.9.125 - kartice za deljenje su Filipov crtac v2 (Atlas paleta, ZR Coast, 11 kompozicija, ulazna animacija, video). v52: 0.9.124 - Filipova grana: ZR Coast 300-500 u jednom fajlu (MENJA URL pisma, kes MORA da padne), uloge pisma, znak sa autoputa, porodica ikonica, ikone i splash iz alata, pravne strane na brend tokenima. v51: 0.9.123 - Podeli voznju = Filipov Share studio preko celog ekrana (10 kompozicija na platnu, web/src/share/), stari list #shareTpl povucen. v50: 0.9.122 - Atlas lista ispod trake + nova ikona/splash; 0.9.121 - nagib se meri i u pozadini (CoreMotion kroz nativni most, replay kroz isto jezgro); 0.9.120 - Atlas identitet uzivo (Archivo + ZR Coast self-hostovani, nova paleta, brzo R), brojevi u voznji privremeno Archivo 800; required-shell install gate, bounded fallback and scoped cache cleanup; Archivo self-hosted (Google Fonts CSS left PRECACHE). v49: Atlas identitet (grana filip/app-structure, jos NIJE pusteno) - Archivo + ZR Coast menjaju PRECACHE URL pisma, a kes pisma trazi sa ignoreSearch, pa bi bez novog imena kesa stari CSS (Saira/JetBrains) odgovarao na novi zahtev. Kes MORA da padne. v48: 0.9.119 - nagib koji nije meren vise se ne prikazuje kao nula (jedno merilo za sazetak i sve tri deljene kartice) + pokrivenost merenja. v47: 0.9.118 - trag leze NA PUTU: gustina 20 m umesto 313 m (pakovan zapis), snimak i replay lepe trag na puteve kao i sazetak. v46: 0.9.117 - replay se pomera po PUTU (2,5% ekrana po kadru), zum prati brzinu; rucni opseg kroz isti list; greske na srpskom; Atlas bez duplog zaglavlja. v45: 0.9.116 - list "Snimak voznje": app predlaze isecke, kapa 60 s, iskrena traka napretka. v44: 0.9.115 - izvoz videa prepisan: prostorni korak 8 m po kadru, trajanje iz kilometraze, izbor deonice. v43: 0.9.114 - kratak Google link (maps.app.goo.gl) se prati do tacke; kad se ne moze, app to kaze. v42: 0.9.113 - pauze u replayu/videu, traka u dva reda, dvosmerno prevlacenje, vidljivi pinovi. v41: 0.9.112 - prekidac 3D/2D u replayu, ravan pogled vraca nagib. v40: 0.9.111 - promena taba gasi sazetak voznje. v39: 0.9.110 - izvoz replaya kao video (vanekranska mapa + MediaRecorder). v38: 0.9.109 - 3D replay iz prvog lica sa zastancima na trenucima. v37: 0.9.108 - klizne brojke u voznji (brzina/visina/temperatura). v36: 0.9.107 - polazak se posle voznje vraca na trenutnu lokaciju, Atlas mapa 2/3. v35: 0.9.106 - preostalo vreme u voznji, Atlas izlog se ne zaglavljuje, Uvezi GPX u traci Atlasa. v34: 0.9.105 - dijalozi ostavljaju trajan trag (mr_dijalog) i ulaze u izvoz. v33: 0.9.104 - pretraga po imenu (bravar vise nije prvi red), Enter ne bira kad je vrh neresen, polja OD/DO kroz isti lanac. v32: 0.9.103 - teren 27.8.: provera verzije (nova ljuska MORA da padne u telefon), nagib posle pauze, sazetak ne pojede meni, Breza 10, koridori kroz terenske ocene, X u oblacicu i replayu. v31: 0.9.102 - svih 11 odobrenih nalaza (13, 34, 35, 37, 38, 78, 88, 95, 96, 97, 106). v30: 0.9.101 - politika privatnosti nabraja umesto da broji (nalaz 61); privatnost.html NIJE u PRECACHE pa nov tekst stize pri prvom otvaranju sa signalom. v29: 0.9.100 - Boskove odluke o pauzi (105c, 73, 75): izlaz priznaje odmak od 150 m, rucna pauza se gasi sama posle 2 min istrajne voznje i to kaze, stajanje od 3 min ostaje u dnevniku. v28: 0.9.99 - dve regresije iz 0.9.98 uhvacene pre voznje (histereza opoziva dolaska; poruka "nemam uputstva" vise ne gazi "Van rute"). v27: 0.9.98 - runda iskrenosti (nalazi 11, 26, 27, 39, 54, 56, 62, 69, 83, 94, 103): app prestaje da tvrdi ono sto nema cime da potkrepi i da cuti o onome sto je uradio. Plocice i teren OSTAJU - njihova imena vise ne nose V. v26: 0.9.97 - plocice i teren vise NE nose verziju u imenu kesa (nalaz 85: svaki apdejt je brisao mapu, pa je prva voznja bez signala bila bez podloge) + pozadinski paket ne laze nativni sloj (nalaz 99). OVAJ activate JOS JEDNOM brise stari rmr-v25-plocice - ime nosi verziju, drugacije se ne moze - i to je POSLEDNJI put. v25: 0.9.96 - rupe u tragu se broje i javljaju (QA nalaz 100); nova ljuska MORA da padne u telefon. v24: 0.9.95 - kljuc kesa vise ne nosi upit (bez signala se servirala NAJSTARIJA kopija svakog podatka, QA nalaz 53) + noc popravki 27.8.; nova ljuska MORA da padne u telefon. v23: 0.9.90 Atlas deonica (rezim nad mapom iz taba Rute: sve deonice u jednoj boji, kartica sa ocenama zajednice, "Vodi me preko nje") - nova ljuska mora da padne u telefon (25.8.). v22: 0.9.89 ocene deonica (kartica u sazetku + mr_ocene overlay + prijave kanal bez koordinata) - nova ljuska mora da padne u telefon (25.8.). v21: 0.9.88 mini-runda presuda (drugi slot za pecene, mr_defRuta, "Vozi i ti" link, Povezi voznje u turu) - nova ljuska mora da padne u telefon (25.8.). v20: 0.9.87 pecena baza kuriranih deonica (unija za sivenje u loadPutevi) - nova ljuska mora da padne u telefon (25.8.). v19: 0.9.86 zaokruzi turu - ture sa etapama, dnevnik cap 30 - nova ljuska mora da padne u telefon (25.8.). v18: 0.9.85 presude 24.8. - kombinovana podrazumevana + svih 63 deonica u igri - nova ljuska mora da padne u telefon (24.8.). v17: 0.9.84 kurirano sivenje (kombinovana zna za dobre deonice iz baze zajednice) - nova ljuska mora da padne u telefon (24.8.). v16: 0.9.83 auto-pauza + pozadinski GPS most (fixKorak/rmrGpsPaket) - nova ljuska mora da padne u telefon (24.8.). v15: 0.9.82 runda 5 terenskih popravki (checkpoint voznje, nagib jedan izvor, snap trag, reroute paint-first, planner leak, ime cilja) - nova ljuska mora da padne u telefon (24.8.). v14: HUD identitet 0.9.79 - novo pismo (Saira Semi Condensed + JetBrains Mono) menja PRECACHE URL, pa stari kes koji jos drzi Archivo MORA da padne (16.8.). v13: test.html -> app.html; stari kes drzi staru ljusku pod starim imenom, MORA da padne (16.8.). v12: 0.9.78 altApply hibrid fix (16.8.). v11: 0.9.77 - pauza radar/prognoza, Druga ruta, tihe potvrde, pravne stranice (16.8.). v10: mesta_zajednice.json promenjeno (10 koordinata vraceno na prava mesta, 13.8.). v9: izbacen unos-pretpostavka. v7: preimenovani data fajlovi - stari kes mora da padne */
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
  "./data/prelazi.json",
  "./data/mesta_zajednice.json",
  "./data/pumpe.json",
  "./data/restorani.json",
  "./data/skupovi.json",
  "./data/countries_bbox.json",
  "./data/manifest.webmanifest",
  "https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js",
  "https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css",
  "./fonts/Archivo-Variable-latin.woff2",       // Archivo: sav tekst, self-hostovan (15.9.2026)
  "./fonts/Archivo-Variable-latin-ext.woff2",   // c c s z dj
  "./fonts/ZRCoast.woff2",   // ZR Coast: svi brojevi, tezine 300-500 u jednom fajlu (15.9.2026), self-hostovan
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

// An update is usable only when the app, essential data, library and fonts exist.
// Landing and map style/sprites warm opportunistically; the previous shell remains a fallback.
const REQUIRED = PRECACHE.filter(u => u !== "./" && !u.startsWith("https://tiles.openfreemap.org/"));
const NETWORK_TIMEOUT_MS = 8000;
async function fetchBounded(request) {
  const controller = new AbortController();
  let timer;
  try {
    return await Promise.race([
      fetch(request, { signal: controller.signal }),
      new Promise((_, reject) => { timer = setTimeout(() => { controller.abort(); reject(new Error("Network timeout")); }, NETWORK_TIMEOUT_MS); })
    ]);
  } finally { clearTimeout(timer); }
}
self.addEventListener("install", (e) => {
  e.waitUntil((async () => {
    const c = await caches.open(LJUSKA);
    const results = await Promise.allSettled(PRECACHE.map(async u => {
      const request = new Request(u, { cache: "reload" });
      const response = await fetchBounded(request);
      if (!response.ok) throw new Error(`Precache HTTP ${response.status}: ${u}`);
      await c.put(request, response);
    }));
    const missing = REQUIRED.filter(u => results[PRECACHE.indexOf(u)].status === "rejected");
    if (missing.length) {
      // All writes have settled before deletion; late responses cannot recreate a partial shell.
      await caches.delete(LJUSKA);
      throw new Error(`Update incomplete: ${missing.join(", ")}`);
    }
    await self.skipWaiting();
  })());
});
self.addEventListener("activate", (e) => {
  e.waitUntil((async () => {
    const shells = (await caches.keys()).filter(k => /^rmr-v\d+-ljuska$/.test(k) && k !== LJUSKA);
    const previous = shells.at(-1);
    for (const k of shells) if (k !== previous) await caches.delete(k);
    // Other apps' caches, map tiles, DEM, and the previous RMR shell stay intact.
    await self.clients.claim();
  })());
});
async function shellFallback(request, options) {
  const current = await caches.open(LJUSKA);
  const hit = await current.match(request, options);
  if (hit) return hit;
  const previous = (await caches.keys()).filter(k => /^rmr-v\d+-ljuska$/.test(k) && k !== LJUSKA).at(-1);
  return previous ? (await caches.open(previous)).match(request, options) : undefined;
}

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

  // App HTML belongs to the installed shell. A later network response must not replace
  // a working offline app before its worker/dependencies have passed the install gate.
  if (istiKoren && url.pathname === new URL("./app.html", self.location).pathname) {
    e.respondWith((async () => {
      const cached = await shellFallback(new URL("./app.html", self.location).href);
      if (cached) return cached;
      try { return await fetchBounded(req); } catch { return Response.error(); }
    })());
    return;
  }

  // PODACI: mreza prvo, kes samo kao rezerva.
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
        const r = await fetchBounded(req);
        if (!r.ok) return (await shellFallback(kljuc)) || r;
        if (r && r.ok) { try { await c.put(new Request(kljuc), r.clone()); await ogranici(LJUSKA, LJUSKA_MAX, CUVAJ); } catch { /* Cache quota must not hide a fresh network response. */ } }   // 0.9.95 (nalaz 92): rez koji NE dira precache
        return r;
      } catch (err) {
        // JSON and unrelated documents must never receive app HTML as a fake success.
        return (await shellFallback(kljuc)) ||
               (await shellFallback(req, { ignoreSearch: true })) || Response.error();
      }
    })());
    return;
  }

  // ostatak ljuske: biblioteka, font, staticki podaci - kes prvo, osvezavanje u pozadini
  if (istiKoren || LJUSKA_HOST.test(url.host)) {
    e.respondWith((async () => {
      const c = await caches.open(LJUSKA);
      const iz = await shellFallback(req, { ignoreSearch: true });
      const sveze = fetchBounded(req).then(async (r) => { if (r && r.ok) try { await c.put(req, r.clone()); } catch {} return r; }).catch(() => null);
      if (iz) { sveze; return iz; }
      const r = await sveze;
      return r || Response.error();
    })());
  }
});
