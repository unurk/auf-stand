/**
 * Formatierung aller Zahlen und Zeiträume. Nichts wird in der UI von Hand
 * zusammengesetzt, damit Darstellung und Fehlwert-Behandlung überall gleich sind.
 */

import type { MetricKey } from "@/data/types";

/** Einheitlicher Text für jeden fehlenden Wert. */
export const KEINE_DATEN = "[Keine Daten verfügbar]";

/**
 * Zahlen werden mit de-DE formatiert: Punkt als Tausendertrennung, Komma als
 * Dezimaltrennung — die im österreichischen Druck übliche Schreibweise. Das
 * ICU-Muster für de-AT gruppiert mit einem schmalen Leerzeichen und weicht
 * damit von der Erwartung der Leserinnen und Leser ab. Monatsnamen kommen
 * ohnehin aus der eigenen Liste unten (inklusive „Jänner").
 */
const LOCALE = "de-DE";

const MONTHS = [
  "Jänner",
  "Februar",
  "März",
  "April",
  "Mai",
  "Juni",
  "Juli",
  "August",
  "September",
  "Oktober",
  "November",
  "Dezember",
];

function nullable(
  value: number | null | undefined,
  render: (value: number) => string,
): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return KEINE_DATEN;
  }
  return render(value);
}

/**
 * Ganze Euro, z. B. „7.240 €".
 *
 * Bewusst nicht über style:"currency": de-AT stellt das Zeichen dort voran
 * („€ 7.240"), was zusammen mit dem Zusatz „/ m²" schlecht lesbar wird.
 */
export function formatEuro(value: number | null | undefined): string {
  return nullable(
    value,
    (v) =>
      `${new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 0 }).format(v)} €`,
  );
}

/** Euro mit zwei Nachkommastellen, z. B. „17,40 €" */
export function formatEuroPrecise(value: number | null | undefined): string {
  return nullable(
    value,
    (v) =>
      `${new Intl.NumberFormat(LOCALE, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(v)} €`,
  );
}

/** Kaufpreis je m², z. B. „7.240 € / m²" */
export function formatSalePerSqm(value: number | null | undefined): string {
  return nullable(value, (v) => `${formatEuro(v)} / m²`);
}

/** Miete je m² und Monat, z. B. „17,40 € / m²" */
export function formatRentPerSqm(value: number | null | undefined): string {
  return nullable(value, (v) => `${formatEuroPrecise(v)} / m²`);
}

/** Prozent mit Vorzeichen, z. B. „+2,4 %" */
export function formatPercent(
  value: number | null | undefined,
  fractionDigits = 1,
): string {
  return nullable(value, (v) => {
    const formatted = new Intl.NumberFormat(LOCALE, {
      minimumFractionDigits: fractionDigits,
      maximumFractionDigits: fractionDigits,
    }).format(Math.abs(v));
    const sign = v > 0 ? "+" : v < 0 ? "−" : "±";
    return `${sign}${formatted} %`;
  });
}

/** Prozent ohne Vorzeichen, z. B. „2,4 %" */
export function formatPercentPlain(
  value: number | null | undefined,
  fractionDigits = 1,
): string {
  return nullable(
    value,
    (v) =>
      `${new Intl.NumberFormat(LOCALE, {
        minimumFractionDigits: fractionDigits,
        maximumFractionDigits: fractionDigits,
      }).format(v)} %`,
  );
}

/** Fläche, z. B. „68,4 m²" */
export function formatSqm(value: number | null | undefined): string {
  return nullable(
    value,
    (v) =>
      `${new Intl.NumberFormat(LOCALE, {
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
      }).format(v)} m²`,
  );
}

/** Anzahl, z. B. „1.240" */
export function formatCount(value: number | null | undefined): string {
  return nullable(value, (v) =>
    new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 0 }).format(v),
  );
}

/** Zahl mit einer Nachkommastelle, z. B. „31,2" */
export function formatDecimal(
  value: number | null | undefined,
  fractionDigits = 1,
): string {
  return nullable(value, (v) =>
    new Intl.NumberFormat(LOCALE, {
      minimumFractionDigits: fractionDigits,
      maximumFractionDigits: fractionDigits,
    }).format(v),
  );
}

/** Periode „2026-06" → „Juni 2026" */
export function formatPeriod(period: string | null | undefined): string {
  if (!period) return KEINE_DATEN;
  const [year, month] = period.split("-");
  const name = MONTHS[Number(month) - 1];
  if (!name || !year) return period;
  return `${name} ${year}`;
}

/** Kurzform „2026-06" → „06/26", für Diagrammachsen */
export function formatPeriodShort(period: string): string {
  const [year, month] = period.split("-");
  if (!year || !month) return period;
  return `${month}/${year.slice(2)}`;
}

/** ISO-Datum „2026-07-02" → „2. Juli 2026" */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return KEINE_DATEN;
  const date = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return KEINE_DATEN;
  return `${date.getUTCDate()}. ${MONTHS[date.getUTCMonth()]} ${date.getUTCFullYear()}`;
}

export const METRIC_LABELS: Record<MetricKey, string> = {
  salePricePerSqm: "Angebotspreis Kauf",
  rentPricePerSqm: "Angebotsmiete",
  listingsCount: "Inserate",
  averageSizeSqm: "Ø Wohnungsgröße",
};

export const METRIC_UNITS: Record<MetricKey, string> = {
  salePricePerSqm: "€ / m²",
  rentPricePerSqm: "€ / m² und Monat",
  listingsCount: "Anzahl",
  averageSizeSqm: "m²",
};

/** Formatiert einen Wert passend zu seiner Kennzahl. */
export function formatMetric(
  value: number | null | undefined,
  metric: MetricKey,
): string {
  switch (metric) {
    case "salePricePerSqm":
      return formatSalePerSqm(value);
    case "rentPricePerSqm":
      return formatRentPerSqm(value);
    case "listingsCount":
      return formatCount(value);
    case "averageSizeSqm":
      return formatSqm(value);
  }
}

/** Absolute Veränderung mit Vorzeichen, passend zur Kennzahl formatiert. */
export function formatMetricDelta(
  value: number | null | undefined,
  metric: MetricKey,
): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return KEINE_DATEN;
  }
  const sign = value > 0 ? "+" : value < 0 ? "−" : "±";
  return `${sign}${formatMetric(Math.abs(value), metric)}`;
}

/**
 * Kurzform für Diagrammachsen: nur die Zahl, ohne Einheit, aber mit
 * derselben Trennzeichen-Konvention wie überall sonst.
 */
export function formatAxisNumber(value: number, metric: MetricKey): string {
  return new Intl.NumberFormat(LOCALE, {
    maximumFractionDigits: metric === "rentPricePerSqm" ? 1 : 0,
  }).format(value);
}

/** Richtung einer Veränderung — für Symbol, Farbe und Textbeschreibung. */
export function changeDirection(
  percent: number | null | undefined,
): "up" | "down" | "flat" | "unknown" {
  if (percent === null || percent === undefined || !Number.isFinite(percent)) {
    return "unknown";
  }
  if (percent > 0.05) return "up";
  if (percent < -0.05) return "down";
  return "flat";
}
