/**
 * Repository-Fassade — der einzige Zugriffspunkt auf Daten.
 *
 * Kein Modul außerhalb von src/data importiert die Fixtures direkt. Wird später
 * eine echte Datenquelle angebunden, wird nur dieses Modul umgestellt (ggf. auf
 * asynchrone Aufrufe); Seiten und Berechnungen bleiben unverändert.
 */

import observationsData from "./observations.json";
import { regions } from "./regions";
import { insights } from "./insights";
import { issues } from "./issues";
import { currentPeriod, dataSource } from "./source";
import type {
  DataSourceInfo,
  EditorialInsight,
  MarketObservation,
  Region,
  ReportIssue,
} from "./types";

const allObservations = observationsData.observations as MarketObservation[];

/** Alle im Datensatz vorhandenen Perioden, aufsteigend sortiert. */
export const periods: string[] = [...observationsData.periods].sort();

export function getRegions(): Region[] {
  return regions;
}

export function getRegion(regionId: string): Region | undefined {
  return regions.find((region) => region.id === regionId);
}

/**
 * Beobachtungen einer Region, aufsteigend nach Periode.
 * `months` schneidet auf die jüngsten n Perioden zu.
 */
export function getObservations(
  regionId: string,
  months?: number,
): MarketObservation[] {
  const series = allObservations
    .filter((observation) => observation.regionId === regionId)
    .sort((a, b) => a.period.localeCompare(b.period));

  if (months === undefined) return series;
  return series.slice(-months);
}

/** Beobachtungen mehrerer Regionen, als Map je regionId. */
export function getObservationsForRegions(
  regionIds: string[],
  months?: number,
): Record<string, MarketObservation[]> {
  const result: Record<string, MarketObservation[]> = {};
  for (const regionId of regionIds) {
    result[regionId] = getObservations(regionId, months);
  }
  return result;
}

/** Der jüngste Datenpunkt einer Region — oder undefined, wenn keiner existiert. */
export function getLatestObservation(
  regionId: string,
): MarketObservation | undefined {
  const series = getObservations(regionId);
  return series.at(-1);
}

export function getInsightForRegion(
  regionId: string,
  period: string = currentPeriod,
): EditorialInsight | undefined {
  return insights.find(
    (insight) => insight.regionId === regionId && insight.period === period,
  );
}

/** Übergreifende Einordnung einer Ausgabe (ohne regionId). */
export function getOverviewInsight(
  period: string = currentPeriod,
): EditorialInsight | undefined {
  return insights.find(
    (insight) => insight.regionId === undefined && insight.period === period,
  );
}

/** Ausgaben, neueste zuerst. */
export function getIssues(): ReportIssue[] {
  return [...issues].sort((a, b) =>
    b.publicationDate.localeCompare(a.publicationDate),
  );
}

export function getIssue(issueId: string): ReportIssue | undefined {
  return issues.find((issue) => issue.id === issueId);
}

export function getCurrentIssue(): ReportIssue | undefined {
  return getIssues()[0];
}

export function getDataSource(): DataSourceInfo {
  return dataSource;
}

export function getCurrentPeriod(): string {
  return currentPeriod;
}

export type {
  DataSourceInfo,
  EditorialInsight,
  MarketObservation,
  MetricKey,
  Region,
  ReportIssue,
} from "./types";
