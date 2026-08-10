/**
 * Generator für die synthetischen Beispieldaten des Prototypen.
 *
 * WICHTIG: Hier entstehen KEINE echten Marktdaten. Es gibt derzeit keine
 * bestätigte Datenpartnerschaft und keinen bestätigten Datenzugang. Die Werte
 * sind frei erfunden und lediglich so parametrisiert, dass sie plausibel
 * aussehen und die UI sinnvoll ausgelastet wird.
 *
 * Der Generator läuft deterministisch (fester Seed): ein erneuter Lauf erzeugt
 * dieselbe Datei. Das Ergebnis wird eingecheckt, damit die App ohne Buildschritt
 * stabil dieselben Zahlen zeigt.
 *
 * Aufruf:  npm run generate:data
 *
 * SPÄTERE INTEGRATION: Dieses Skript ist der vorgesehene Austauschpunkt. Wird
 * eine echte Quelle angeschlossen, ersetzt deren Abruf die Zufallserzeugung —
 * das Ausgabeformat (src/data/observations.json) und damit die gesamte App
 * bleiben unverändert. Zusätzlich muss dann DataSourceInfo.status in
 * src/data/source.ts von "demo" auf "verified" gehoben werden.
 */

import { writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const OUT_FILE = join(
  dirname(fileURLToPath(import.meta.url)),
  "..",
  "src",
  "data",
  "observations.json",
);

const SEED = 20260610;
const MONTHS = 24;
const LAST_PERIOD = "2026-06";

/** Deterministischer PRNG (Mulberry32) — kein Math.random, damit reproduzierbar. */
function createRandom(seed) {
  let a = seed >>> 0;
  return function random() {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Profile je Region: Startniveau und jährliche Dynamik.
 * trend = jährliche Veränderung in Prozent, als Erzählung gedacht
 * (Kernstädte teuer mit abflachender Dynamik, Umland günstiger mit Aufholeffekt).
 */
const PROFILES = [
  { id: "wien-neubau",     sale: 7150, saleTrend:  1.4, rent: 17.4, rentTrend: 4.6, listings: 310, listingsTrend: -7,  size: 68 },
  { id: "wien-donaustadt", sale: 5240, saleTrend:  0.4, rent: 14.1, rentTrend: 3.8, listings: 690, listingsTrend:  4,  size: 74 },
  { id: "graz",            sale: 4560, saleTrend:  1.1, rent: 12.6, rentTrend: 4.1, listings: 520, listingsTrend: -2,  size: 66 },
  { id: "salzburg-stadt",  sale: 6890, saleTrend:  2.2, rent: 16.2, rentTrend: 5.0, listings: 240, listingsTrend: -9,  size: 71 },
  { id: "linz",            sale: 4180, saleTrend:  0.2, rent: 11.4, rentTrend: 3.2, listings: 430, listingsTrend:  1,  size: 73 },
  { id: "innsbruck",       sale: 6420, saleTrend:  1.8, rent: 15.5, rentTrend: 4.8, listings: 200, listingsTrend: -6,  size: 64 },
  { id: "st-poelten",      sale: 3240, saleTrend:  2.8, rent:  9.8, rentTrend: 5.4, listings: 180, listingsTrend: 11,  size: 78 },
  { id: "klagenfurt",      sale: 3480, saleTrend: -0.6, rent: 10.2, rentTrend: 2.4, listings: 160, listingsTrend: -3,  size: 76 },
];

/**
 * Absichtliche Datenlücken. Der Prototyp soll zeigen, dass fehlende Werte
 * sauber als „[Keine Daten verfügbar]" behandelt und nicht als 0 gerechnet werden.
 */
const GAPS = {
  // Kleiner Markt: die Mietauswertung ist zuletzt unter die Meldeschwelle gefallen.
  "klagenfurt": { field: "rentPricePerSqm", periods: ["2026-05", "2026-06"] },
  // Erhebung startet später: die ersten fünf Monate fehlen komplett.
  "st-poelten": { missingPeriods: ["2024-07", "2024-08", "2024-09", "2024-10", "2024-11"] },
};

function buildPeriods(lastPeriod, count) {
  const [lastYear, lastMonth] = lastPeriod.split("-").map(Number);
  const periods = [];
  for (let i = count - 1; i >= 0; i -= 1) {
    const total = lastYear * 12 + (lastMonth - 1) - i;
    const year = Math.floor(total / 12);
    const month = (total % 12) + 1;
    periods.push(`${year}-${String(month).padStart(2, "0")}`);
  }
  return periods;
}

/** Leichter Jahresgang: im Frühjahr etwas mehr Inserate als im Winter. */
function seasonalListingsFactor(period) {
  const month = Number(period.split("-")[1]);
  return 1 + 0.11 * Math.sin(((month - 3) / 12) * 2 * Math.PI);
}

function main() {
  const random = createRandom(SEED);
  const periods = buildPeriods(LAST_PERIOD, MONTHS);
  const observations = [];

  for (const profile of PROFILES) {
    const gap = GAPS[profile.id] ?? {};
    const missingPeriods = new Set(gap.missingPeriods ?? []);
    const gapPeriods = new Set(gap.periods ?? []);

    periods.forEach((period, index) => {
      if (missingPeriods.has(period)) return;

      // Monatsanteil des Jahrestrends plus etwas Rauschen.
      const progress = index / 12;
      const saleFactor =
        Math.pow(1 + profile.saleTrend / 100, progress) * (1 + (random() - 0.5) * 0.012);
      const rentFactor =
        Math.pow(1 + profile.rentTrend / 100, progress) * (1 + (random() - 0.5) * 0.010);
      const listingsFactor =
        Math.pow(1 + profile.listingsTrend / 100, progress) *
        seasonalListingsFactor(period) *
        (1 + (random() - 0.5) * 0.09);

      const observation = {
        regionId: profile.id,
        period,
        salePricePerSqm: Math.round(profile.sale * saleFactor),
        rentPricePerSqm: Math.round(profile.rent * rentFactor * 10) / 10,
        listingsCount: Math.max(0, Math.round(profile.listings * listingsFactor)),
        averageSizeSqm: Math.round((profile.size + (random() - 0.5) * 3.4) * 10) / 10,
      };

      if (gapPeriods.has(period) && gap.field) {
        observation[gap.field] = null;
      }

      observations.push(observation);
    });
  }

  const payload = {
    _hinweis:
      "Synthetische Beispieldaten. Keine echten Marktdaten, keine bestätigte Datenquelle. Erzeugt von scripts/generate-demo-data.mjs.",
    generator: "scripts/generate-demo-data.mjs",
    seed: SEED,
    periods,
    observations,
  };

  writeFileSync(OUT_FILE, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
  console.log(
    `${observations.length} Beispielwerte für ${PROFILES.length} Regionen und ${periods.length} Perioden geschrieben: ${OUT_FILE}`,
  );
}

main();
