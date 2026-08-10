/**
 * Ableitung der „wichtigsten Marktbewegungen" für das Dashboard.
 *
 * Bewusst regelbasiert und nachvollziehbar: Es werden ausschließlich Extremwerte
 * definierter Reihungen benannt („die stärkste Zunahme im Datensatz"). Es gibt
 * keine Wertung wie „beste Kaufchance" und keine Prognose — beides wäre aus
 * Angebotsdaten nicht ableitbar.
 */

import type { MetricKey } from "@/data/types";
import { getObservationsForRegions, getRegions } from "@/data";
import { rankByChange, rankByLevel, type ChangeResult } from "./metrics";

export type Highlight = {
  id: string;
  regionId: string;
  regionName: string;
  /** Was gemessen wurde — die Methodik in einem Satz. */
  measure: string;
  metric: MetricKey;
  change: ChangeResult | null;
  level: number | null;
};

/** Zeitfenster für die Bewegungen des Dashboards: 12 Monate. */
const HIGHLIGHT_MONTHS = 12;

export function getHighlights(): Highlight[] {
  const regions = getRegions();
  const regionName = (id: string) =>
    regions.find((region) => region.id === id)?.name ?? id;
  const ids = regions.map((region) => region.id);
  const series = getObservationsForRegions(ids, HIGHLIGHT_MONTHS);

  const highlights: Highlight[] = [];

  const rentRise = rankByChange(series, "rentPricePerSqm", "first")[0];
  if (rentRise) {
    highlights.push({
      id: "miete-anstieg",
      regionId: rentRise.regionId,
      regionName: regionName(rentRise.regionId),
      measure: `Stärkster Anstieg der Angebotsmiete über ${HIGHLIGHT_MONTHS} Monate`,
      metric: "rentPricePerSqm",
      change: rentRise.change,
      level: rentRise.change.to,
    });
  }

  const listingsRanking = rankByChange(series, "listingsCount", "first");
  const listingsDrop = listingsRanking.at(-1);
  if (listingsDrop && listingsDrop.regionId !== rentRise?.regionId) {
    highlights.push({
      id: "inserate-rueckgang",
      regionId: listingsDrop.regionId,
      regionName: regionName(listingsDrop.regionId),
      measure: `Stärkster Rückgang der Inseratszahl über ${HIGHLIGHT_MONTHS} Monate`,
      metric: "listingsCount",
      change: listingsDrop.change,
      level: listingsDrop.change.to,
    });
  }

  const saleRanking = rankByChange(series, "salePricePerSqm", "first");
  const saleMove = saleRanking[0];
  if (saleMove && !highlights.some((h) => h.regionId === saleMove.regionId)) {
    highlights.push({
      id: "kauf-anstieg",
      regionId: saleMove.regionId,
      regionName: regionName(saleMove.regionId),
      measure: `Stärkster Anstieg der Angebotspreise über ${HIGHLIGHT_MONTHS} Monate`,
      metric: "salePricePerSqm",
      change: saleMove.change,
      level: saleMove.change.to,
    });
  }

  const saleDrop = saleRanking.at(-1);
  if (
    saleDrop &&
    saleDrop.change.percent < 0 &&
    !highlights.some((h) => h.regionId === saleDrop.regionId)
  ) {
    highlights.push({
      id: "kauf-rueckgang",
      regionId: saleDrop.regionId,
      regionName: regionName(saleDrop.regionId),
      measure: `Einziger Rückgang der Angebotspreise über ${HIGHLIGHT_MONTHS} Monate`,
      metric: "salePricePerSqm",
      change: saleDrop.change,
      level: saleDrop.change.to,
    });
  }

  return highlights;
}

/**
 * Wichtigste Kennzahl einer Ausgabe: die stärkste Veränderung der
 * Angebotsmiete unter den hervorgehobenen Regionen, gemessen von der
 * Vorperiode auf die Periode der Ausgabe.
 *
 * Bewusst aus den Daten berechnet statt in die Ausgabe geschrieben —
 * so können Text und Zahl nicht auseinanderlaufen.
 */
export function getIssueKeyMetric(
  period: string,
  featuredRegionIds: string[],
): Highlight | null {
  const regions = getRegions();
  const seriesUpToPeriod: Record<string, ReturnType<typeof getObservationsForRegions>[string]> =
    {};

  for (const regionId of featuredRegionIds) {
    const series = getObservationsForRegions([regionId])[regionId] ?? [];
    // Nur Perioden bis einschließlich der Ausgabe berücksichtigen.
    seriesUpToPeriod[regionId] = series.filter(
      (observation) => observation.period <= period,
    );
  }

  const ranking = rankByChange(seriesUpToPeriod, "rentPricePerSqm", "previous");
  const top = ranking[0];
  if (!top) return null;

  return {
    id: `issue-${period}`,
    regionId: top.regionId,
    regionName:
      regions.find((region) => region.id === top.regionId)?.name ?? top.regionId,
    measure: "Stärkste Veränderung der Angebotsmiete gegenüber der Vorperiode",
    metric: "rentPricePerSqm",
    change: top.change,
    level: top.change.to,
  };
}

/** Reihung nach aktuellem Kaufpreisniveau — für die freie Kurzübersicht. */
export function getPriceLevelRanking() {
  const regions = getRegions();
  const series = getObservationsForRegions(regions.map((region) => region.id));
  return rankByLevel(series, "salePricePerSqm").map((entry) => ({
    ...entry,
    regionName:
      regions.find((region) => region.id === entry.regionId)?.name ?? entry.regionId,
  }));
}
