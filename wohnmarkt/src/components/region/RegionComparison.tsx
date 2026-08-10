"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { MarketObservation, MetricKey, Region } from "@/data/types";
import {
  changeVsFirst,
  changeVsPrevious,
  compareRegions,
  latestWithValue,
  metricValue,
} from "@/lib/metrics";
import {
  METRIC_LABELS,
  METRIC_UNITS,
  formatMetric,
  formatPercent,
  formatPeriod,
} from "@/lib/format";
import { TimeSeriesChart } from "@/components/charts/TimeSeriesChart";
import { ChartFallbackTable } from "@/components/charts/ChartFallbackTable";
import { ChangeBadge } from "@/components/ui/ChangeBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { AboCta } from "@/components/premium/AboCta";
import { usePremium } from "@/hooks/usePremium";

const METRICS: MetricKey[] = [
  "salePricePerSqm",
  "rentPricePerSqm",
  "listingsCount",
  "averageSizeSqm",
];

const FREE_SLOTS = 2;
const PREMIUM_SLOTS = 4;
const FREE_RANGES = [6, 12] as const;
const PREMIUM_RANGE = 24;

/**
 * Regionenvergleich. Frei sind zwei Regionen und 6/12 Monate;
 * die dritte und vierte Region sowie 24 Monate gehören zum simulierten Abo.
 */
export function RegionComparison({
  regions,
  seriesByRegion,
}: {
  regions: Region[];
  seriesByRegion: Record<string, MarketObservation[]>;
}) {
  const { isPremium, hydrated } = usePremium();
  const [selected, setSelected] = useState<string[]>(() =>
    regions.slice(0, 2).map((region) => region.id),
  );
  const [metric, setMetric] = useState<MetricKey>("salePricePerSqm");
  const [months, setMonths] = useState<number>(12);

  const slots = isPremium ? PREMIUM_SLOTS : FREE_SLOTS;
  const activeIds = selected.slice(0, slots).filter(Boolean);
  const effectiveMonths = !isPremium && months > 12 ? 12 : months;

  const scoped = useMemo(() => {
    const result: Record<string, MarketObservation[]> = {};
    for (const id of activeIds) {
      result[id] = (seriesByRegion[id] ?? []).slice(-effectiveMonths);
    }
    return result;
  }, [activeIds, seriesByRegion, effectiveMonths]);

  const rows = useMemo(() => compareRegions(scoped, metric), [scoped, metric]);

  const regionName = (id: string) =>
    regions.find((region) => region.id === id)?.name ?? id;

  const chartSeries = activeIds.map((id) => ({
    regionId: id,
    label: regionName(id),
  }));

  const setSlot = (index: number, regionId: string) => {
    setSelected((current) => {
      const next = [...current];
      next[index] = regionId;
      return next.filter((id, position) => id && next.indexOf(id) === position);
    });
  };

  const removeSlot = (index: number) => {
    setSelected((current) => current.filter((_, position) => position !== index));
  };

  const hasValues = rows.some((row) =>
    activeIds.some((id) => row.values[id] !== null),
  );

  const ranges: number[] = isPremium
    ? [...FREE_RANGES, PREMIUM_RANGE]
    : [...FREE_RANGES];

  const slotIndexes = Array.from({ length: slots }, (_, index) => index);

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-line bg-surface p-4 sm:p-5">
        <h2 className="text-xs font-medium tracking-wide text-ink-muted uppercase">
          Regionen auswählen
        </h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {slotIndexes.map((index) => (
            <div key={index}>
              <label
                htmlFor={`region-slot-${index}`}
                className="block text-xs text-ink-muted"
              >
                Region {index + 1}
                {index >= FREE_SLOTS && " (im Abo)"}
              </label>
              <div className="mt-1 flex gap-2">
                <select
                  id={`region-slot-${index}`}
                  value={selected[index] ?? ""}
                  onChange={(event) => setSlot(index, event.target.value)}
                  className="w-full rounded-md border border-line-strong bg-surface px-3 py-2 text-sm text-ink"
                >
                  <option value="">— keine —</option>
                  {regions.map((region) => (
                    <option
                      key={region.id}
                      value={region.id}
                      disabled={
                        selected.includes(region.id) && selected[index] !== region.id
                      }
                    >
                      {region.name}
                    </option>
                  ))}
                </select>
                {selected[index] && (
                  <button
                    type="button"
                    onClick={() => removeSlot(index)}
                    className="rounded-md border border-line-strong px-2.5 py-2 text-xs text-ink-soft hover:border-accent hover:text-accent"
                  >
                    Entfernen
                    <span className="sr-only">: {regionName(selected[index])}</span>
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>

        {hydrated && !isPremium && (
          <p className="mt-3 rounded-md bg-paper px-3 py-2 text-xs text-ink-muted">
            Frei vergleichbar sind zwei Regionen über bis zu zwölf Monate. Der
            Vergleich von bis zu {PREMIUM_SLOTS} Regionen und die Reihe über{" "}
            {PREMIUM_RANGE} Monate gehören zum simulierten Abo-Bereich.
          </p>
        )}

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
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
      </div>

      {activeIds.length < 2 ? (
        <EmptyState
          title="Mindestens zwei Regionen auswählen"
          description="Der Vergleich braucht zwei Regionen. Wähle oben aus der Liste — die Auswahl lässt sich jederzeit ändern."
        />
      ) : (
        <>
          <div className="rounded-lg border border-line bg-surface p-4 sm:p-5">
            <p className="text-xs text-ink-muted">
              {METRIC_LABELS[metric]} in {METRIC_UNITS[metric]} · {effectiveMonths}{" "}
              Monate
            </p>
            <div className="mt-3">
              {hasValues ? (
                <TimeSeriesChart
                  rows={rows}
                  series={chartSeries}
                  metric={metric}
                  description={`Vergleich von ${chartSeries
                    .map((entry) => entry.label)
                    .join(" und ")}.`}
                />
              ) : (
                <EmptyState
                  title="Keine Daten verfügbar"
                  description={`Für die gewählten Regionen liegen im gewählten Zeitraum keine Werte zu „${METRIC_LABELS[metric]}“ vor.`}
                />
              )}
            </div>
            {hasValues && (
              <ChartFallbackTable
                periods={rows.map((row) => row.period)}
                series={chartSeries.map((entry) => ({
                  ...entry,
                  values: Object.fromEntries(
                    rows.map((row) => [row.period, row.values[entry.regionId]]),
                  ),
                }))}
                metric={metric}
                caption={`${METRIC_LABELS[metric]} im Vergleich je Zeitraum`}
              />
            )}
          </div>

          <div className="table-scroll rounded-lg border border-line bg-surface">
            <table className="w-full min-w-[32rem] border-collapse text-sm">
              <caption className="px-4 py-3 text-left text-xs text-ink-muted">
                Vergleichstabelle: {METRIC_LABELS[metric]}, Zeitraum{" "}
                {effectiveMonths} Monate
              </caption>
              <thead>
                <tr className="border-y border-line text-left">
                  <th scope="col" className="px-4 py-3 font-medium text-ink-muted">
                    Region
                  </th>
                  <th scope="col" className="px-4 py-3 font-medium text-ink-muted">
                    Aktuell
                  </th>
                  <th scope="col" className="px-4 py-3 font-medium text-ink-muted">
                    ggü. Vorperiode
                  </th>
                  <th scope="col" className="px-4 py-3 font-medium text-ink-muted">
                    über den Zeitraum
                  </th>
                  <th scope="col" className="px-4 py-3 font-medium text-ink-muted">
                    Stand
                  </th>
                </tr>
              </thead>
              <tbody>
                {activeIds.map((id) => {
                  const series = scoped[id] ?? [];
                  const latest = latestWithValue(series, metric);
                  const overall = changeVsFirst(series, metric);
                  return (
                    <tr key={id} className="border-b border-line/60 last:border-0">
                      <th scope="row" className="px-4 py-2.5 text-left font-normal">
                        <Link
                          href={`/regionen/${id}`}
                          className="text-ink hover:text-accent hover:underline underline-offset-2"
                        >
                          {regionName(id)}
                        </Link>
                      </th>
                      <td className="px-4 py-2.5 tabular-nums text-ink">
                        {formatMetric(metricValue(latest, metric), metric)}
                      </td>
                      <td className="px-4 py-2.5">
                        <ChangeBadge
                          change={changeVsPrevious(series, metric)}
                          metric={metric}
                        />
                      </td>
                      <td className="px-4 py-2.5 tabular-nums text-ink-soft">
                        {formatPercent(overall?.percent ?? null)}
                      </td>
                      <td className="px-4 py-2.5 text-ink-muted">
                        {formatPeriod(latest?.period)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}

      <AboCta
        title="Mehr Regionen nebeneinander"
        description={`Im Abo lassen sich bis zu ${PREMIUM_SLOTS} Regionen über ${PREMIUM_RANGE} Monate vergleichen — und die Auswahl bleibt als Beobachtungsliste erhalten.`}
        compact
      />
    </div>
  );
}
