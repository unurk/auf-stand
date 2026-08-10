/**
 * Alle Berechnungen des Prototypen. Reine Funktionen ohne Zustand.
 *
 * Grundregel: Fehlt ein Wert, ist das Ergebnis `null` — nie 0, nie geschätzt,
 * nie der Vormonatswert. Die UI macht daraus „[Keine Daten verfügbar]".
 */

import type { MarketObservation, MetricKey } from "@/data/types";

export type ChangeResult = {
  /** Absolute Veränderung in der Einheit der Kennzahl */
  absolute: number;
  /** Relative Veränderung in Prozent */
  percent: number;
  from: number;
  to: number;
  fromPeriod: string;
  toPeriod: string;
};

/** Wert einer Kennzahl aus einer Beobachtung, `null` wenn nicht vorhanden. */
export function metricValue(
  observation: MarketObservation | undefined,
  metric: MetricKey,
): number | null {
  if (!observation) return null;
  const value = observation[metric];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

/** Jüngste Beobachtung mit einem vorhandenen Wert für die Kennzahl. */
export function latestWithValue(
  series: MarketObservation[],
  metric: MetricKey,
): MarketObservation | undefined {
  for (let i = series.length - 1; i >= 0; i -= 1) {
    if (metricValue(series[i], metric) !== null) return series[i];
  }
  return undefined;
}

/** Älteste Beobachtung mit einem vorhandenen Wert für die Kennzahl. */
export function firstWithValue(
  series: MarketObservation[],
  metric: MetricKey,
): MarketObservation | undefined {
  return series.find((observation) => metricValue(observation, metric) !== null);
}

function buildChange(
  from: MarketObservation,
  to: MarketObservation,
  metric: MetricKey,
): ChangeResult | null {
  const fromValue = metricValue(from, metric);
  const toValue = metricValue(to, metric);
  if (fromValue === null || toValue === null || fromValue === 0) return null;

  return {
    absolute: toValue - fromValue,
    percent: ((toValue - fromValue) / fromValue) * 100,
    from: fromValue,
    to: toValue,
    fromPeriod: from.period,
    toPeriod: to.period,
  };
}

/**
 * Veränderung gegenüber dem vorherigen Zeitraum.
 * Verglichen werden die beiden jüngsten Perioden, für die ein Wert vorliegt —
 * eine Lücke dazwischen überspringt der Vergleich, statt zu scheitern.
 */
export function changeVsPrevious(
  series: MarketObservation[],
  metric: MetricKey,
): ChangeResult | null {
  const withValues = series.filter(
    (observation) => metricValue(observation, metric) !== null,
  );
  if (withValues.length < 2) return null;
  return buildChange(
    withValues[withValues.length - 2],
    withValues[withValues.length - 1],
    metric,
  );
}

/** Veränderung gegenüber dem ersten verfügbaren Zeitraum der Reihe. */
export function changeVsFirst(
  series: MarketObservation[],
  metric: MetricKey,
): ChangeResult | null {
  const first = firstWithValue(series, metric);
  const last = latestWithValue(series, metric);
  if (!first || !last || first.period === last.period) return null;
  return buildChange(first, last, metric);
}

/**
 * Durchschnitt einer Kennzahl über mehrere Regionen zu einer Periode.
 * Regionen ohne Wert werden ausgelassen (nicht als 0 gewertet).
 */
export function averageAcrossRegions(
  seriesByRegion: Record<string, MarketObservation[]>,
  metric: MetricKey,
  period?: string,
): number | null {
  const values: number[] = [];

  for (const series of Object.values(seriesByRegion)) {
    const observation = period
      ? series.find((entry) => entry.period === period)
      : latestWithValue(series, metric);
    const value = metricValue(observation, metric);
    if (value !== null) values.push(value);
  }

  if (values.length === 0) return null;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

export type RankingEntry = {
  regionId: string;
  value: number;
  period: string;
};

/**
 * Reihung nach aktuellem Niveau einer Kennzahl (absteigend).
 * Regionen ohne Wert erscheinen nicht in der Reihung.
 */
export function rankByLevel(
  seriesByRegion: Record<string, MarketObservation[]>,
  metric: MetricKey,
): RankingEntry[] {
  const entries: RankingEntry[] = [];

  for (const [regionId, series] of Object.entries(seriesByRegion)) {
    const observation = latestWithValue(series, metric);
    const value = metricValue(observation, metric);
    if (observation && value !== null) {
      entries.push({ regionId, value, period: observation.period });
    }
  }

  return entries.sort((a, b) => b.value - a.value);
}

export type ChangeRankingEntry = {
  regionId: string;
  change: ChangeResult;
};

/**
 * Reihung nach Veränderung einer Kennzahl (absteigend nach Prozent).
 * `basis` wählt den Vergleichszeitraum: Vorperiode oder Reihenbeginn.
 */
export function rankByChange(
  seriesByRegion: Record<string, MarketObservation[]>,
  metric: MetricKey,
  basis: "previous" | "first" = "previous",
): ChangeRankingEntry[] {
  const entries: ChangeRankingEntry[] = [];

  for (const [regionId, series] of Object.entries(seriesByRegion)) {
    const change =
      basis === "previous"
        ? changeVsPrevious(series, metric)
        : changeVsFirst(series, metric);
    if (change) entries.push({ regionId, change });
  }

  return entries.sort((a, b) => b.change.percent - a.change.percent);
}

/**
 * Abstand des aktuellen Werts einer Region zum Durchschnitt aller
 * betrachteten Regionen, in Prozent. `null`, wenn eine Seite fehlt.
 */
export function relativeToAverage(
  series: MarketObservation[],
  seriesByRegion: Record<string, MarketObservation[]>,
  metric: MetricKey,
): number | null {
  const value = metricValue(latestWithValue(series, metric), metric);
  const average = averageAcrossRegions(seriesByRegion, metric);
  if (value === null || average === null || average === 0) return null;
  return ((value - average) / average) * 100;
}

/** Verhältnis Kaufpreis zu Jahresmiete je m² („Kaufpreisfaktor"). */
export function priceToRentRatio(
  observation: MarketObservation | undefined,
): number | null {
  const sale = metricValue(observation, "salePricePerSqm");
  const rent = metricValue(observation, "rentPricePerSqm");
  if (sale === null || rent === null || rent === 0) return null;
  return sale / (rent * 12);
}

export type ComparisonRow = {
  period: string;
  /** Wert je regionId; `null` bedeutet: für diese Periode kein Wert. */
  values: Record<string, number | null>;
};

/**
 * Vergleichsreihe für zwei oder mehr Regionen: eine Zeile je Periode,
 * je Region ein Wert oder `null`. Perioden sind die Vereinigungsmenge
 * aller beteiligten Reihen.
 */
export function compareRegions(
  seriesByRegion: Record<string, MarketObservation[]>,
  metric: MetricKey,
): ComparisonRow[] {
  const periodSet = new Set<string>();
  for (const series of Object.values(seriesByRegion)) {
    for (const observation of series) periodSet.add(observation.period);
  }

  return [...periodSet]
    .sort()
    .map((period) => {
      const values: Record<string, number | null> = {};
      for (const [regionId, series] of Object.entries(seriesByRegion)) {
        const observation = series.find((entry) => entry.period === period);
        values[regionId] = metricValue(observation, metric);
      }
      return { period, values };
    });
}

/** Enthält die Reihe überhaupt einen Wert für die Kennzahl? */
export function hasData(
  series: MarketObservation[],
  metric: MetricKey,
): boolean {
  return series.some((observation) => metricValue(observation, metric) !== null);
}
