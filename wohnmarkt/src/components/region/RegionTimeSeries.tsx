"use client";

import { useMemo, useState } from "react";
import type { MarketObservation, MetricKey } from "@/data/types";
import { METRIC_LABELS, METRIC_UNITS, formatPeriod } from "@/lib/format";
import { changeVsFirst } from "@/lib/metrics";
import { TimeSeriesChart } from "@/components/charts/TimeSeriesChart";
import { ChartFallbackTable } from "@/components/charts/ChartFallbackTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { usePremium } from "@/hooks/usePremium";

const METRICS: MetricKey[] = [
  "salePricePerSqm",
  "rentPricePerSqm",
  "listingsCount",
  "averageSizeSqm",
];

/** Frei zugängliche Zeiträume; 24 Monate sind dem simulierten Abo vorbehalten. */
const FREE_RANGES = [6, 12] as const;
const PREMIUM_RANGE = 24;

/**
 * Zeitreihe einer Region mit Umschaltern für Kennzahl und Zeitraum.
 * Die vollständige Reihe kommt vom Server; hier wird nur zugeschnitten.
 */
export function RegionTimeSeries({
  regionId,
  regionName,
  series,
}: {
  regionId: string;
  regionName: string;
  series: MarketObservation[];
}) {
  const [metric, setMetric] = useState<MetricKey>("salePricePerSqm");
  const [months, setMonths] = useState<number>(12);
  const { isPremium, hydrated } = usePremium();

  const effectiveMonths = !isPremium && months > 12 ? 12 : months;

  const sliced = useMemo(
    () => series.slice(-effectiveMonths),
    [series, effectiveMonths],
  );

  const rows = useMemo(
    () =>
      sliced.map((observation) => ({
        period: observation.period,
        values: { [regionId]: observation[metric] },
      })),
    [sliced, metric, regionId],
  );

  const change = changeVsFirst(sliced, metric);
  const hasValues = sliced.some((observation) => observation[metric] !== null);

  const ranges: number[] = hydrated && isPremium
    ? [...FREE_RANGES, PREMIUM_RANGE]
    : [...FREE_RANGES];

  return (
    <div className="rounded-lg border border-line bg-surface p-4 sm:p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <fieldset>
          <legend className="sr-only">Kennzahl auswählen</legend>
          <div className="flex flex-wrap gap-1.5">
            {METRICS.map((key) => (
              <button
                key={key}
                type="button"
                onClick={() => setMetric(key)}
                aria-pressed={metric === key}
                className={`rounded-md border px-3 py-1.5 text-xs font-medium transition-colors ${
                  metric === key
                    ? "border-accent bg-accent text-white"
                    : "border-line-strong bg-surface text-ink-soft hover:border-accent hover:text-accent"
                }`}
              >
                {METRIC_LABELS[key]}
              </button>
            ))}
          </div>
        </fieldset>

        <fieldset>
          <legend className="sr-only">Zeitraum auswählen</legend>
          <div className="flex gap-1.5">
            {ranges.map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => setMonths(value)}
                aria-pressed={effectiveMonths === value}
                className={`rounded-md border px-3 py-1.5 text-xs font-medium transition-colors ${
                  effectiveMonths === value
                    ? "border-accent bg-accent text-white"
                    : "border-line-strong bg-surface text-ink-soft hover:border-accent hover:text-accent"
                }`}
              >
                {value} Monate
              </button>
            ))}
          </div>
        </fieldset>
      </div>

      <p className="mt-3 text-xs text-ink-muted">
        {METRIC_LABELS[metric]} in {METRIC_UNITS[metric]}
        {sliced.length > 0 && (
          <>
            {" "}
            · {formatPeriod(sliced[0].period)} bis{" "}
            {formatPeriod(sliced[sliced.length - 1].period)}
          </>
        )}
      </p>

      <div className="mt-3">
        {hasValues ? (
          <TimeSeriesChart
            rows={rows}
            series={[{ regionId, label: regionName }]}
            metric={metric}
            description={
              change
                ? `${regionName}: Veränderung seit ${formatPeriod(change.fromPeriod)} um ${change.percent.toFixed(1)} Prozent.`
                : `${regionName}: keine Veränderung berechenbar.`
            }
          />
        ) : (
          <EmptyState
            title="Keine Daten verfügbar"
            description={`Für ${regionName} liegen im gewählten Zeitraum keine Werte zu „${METRIC_LABELS[metric]}“ vor. Der Prototyp schätzt fehlende Werte bewusst nicht.`}
          />
        )}
      </div>

      {hasValues && (
        <ChartFallbackTable
          periods={sliced.map((observation) => observation.period)}
          series={[
            {
              regionId,
              label: regionName,
              values: Object.fromEntries(
                sliced.map((observation) => [observation.period, observation[metric]]),
              ),
            },
          ]}
          metric={metric}
          caption={`${METRIC_LABELS[metric]} für ${regionName} je Zeitraum`}
        />
      )}

      {hydrated && !isPremium && (
        <p className="mt-3 rounded-md bg-paper px-3 py-2 text-xs text-ink-muted">
          Die vollständige Reihe über {PREMIUM_RANGE} Monate ist Teil des simulierten
          Abo-Bereichs.
        </p>
      )}
    </div>
  );
}
