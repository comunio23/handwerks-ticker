/* Service Worker des Handwerks-Tickers.

   Zwei Aufgaben:
   1. Die Seite darf als App installiert werden (Android verlangt dafuer
      einen Service Worker, der Anfragen beantwortet).
   2. Der Ticker funktioniert ohne Netz weiter - wichtig im Beratungs-
      gespraech, in der Bahn oder auf der Baustelle.

   Strategie: IMMER zuerst das Netz fragen, die Antwort in den Speicher
   legen, und nur wenn das Netz nicht antwortet die gemerkte Fassung
   zeigen. Umgekehrt (erst Speicher) waere die Seite schneller, wuerde
   aber alte Meldungen zeigen - bei einem Ticker der schlechtere Tausch.
*/
const SPEICHER = "handwerks-ticker-v1";
const GRUNDBESTAND = [
  "/",
  "/manifest.json",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/icons/apple-touch-icon.png",
];

self.addEventListener("install", e => {
  e.waitUntil((async () => {
    const speicher = await caches.open(SPEICHER);
    // Einzeln statt addAll: Faellt ein Symbol aus, soll nicht die ganze
    // Installation scheitern.
    await Promise.all(GRUNDBESTAND.map(w => speicher.add(w).catch(() => {})));
    self.skipWaiting();
  })());
});

self.addEventListener("activate", e => {
  e.waitUntil((async () => {
    for (const name of await caches.keys()) {
      if (name !== SPEICHER) await caches.delete(name);
    }
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", e => {
  const anfrage = e.request;
  if (anfrage.method !== "GET") return;
  if (new URL(anfrage.url).origin !== self.location.origin) return;

  e.respondWith((async () => {
    const speicher = await caches.open(SPEICHER);
    try {
      const antwort = await fetch(anfrage);
      if (antwort && antwort.ok) speicher.put(anfrage, antwort.clone());
      return antwort;
    } catch (ohneNetz) {
      const gemerkt = await speicher.match(anfrage);
      if (gemerkt) return gemerkt;
      // Beim Aufruf einer Seite notfalls die Startseite zeigen
      if (anfrage.mode === "navigate") {
        const start = await speicher.match("/");
        if (start) return start;
      }
      throw ohneNetz;
    }
  })());
});
