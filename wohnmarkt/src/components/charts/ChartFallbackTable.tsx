import type { MetricKey } from "@/data/types";
import { formatMetric, formatPeriod } from "@/lib/format";

export type FallbackSeries = {
  regionId: string;
  label: string;
  values: Record<string, number | null>;
};

/**
 * Datentabelle zum Diagramm. Zahlen dürfen nie nur visuell vorliegen —
 * die Tabelle ist Barrierefreiheit und Beleg zugleich.
 */
export function ChartFallbackTable({
  periods,
  series,
  metric,
  caption,
}: {
  periods: string[];
  series: FallbackSeries[];
  metric: MetricKey;
  caption: string;
}) {
  return (
    <details className="mt-3 rounded-lg border border-line bg-surface">
      <summary className="cursor-pointer px-4 py-2.5 text-sm font-medium text-accent">
        Zahlen zum Diagramm anzeigen
      </summary>
      <div className="table-scroll border-t border-line px-4 py-3">
        <table className="w-full min-w-[24rem] border-collapse text-sm">
          <caption className="sr-only">{caption}</caption>
          <thead>
            <tr className="border-b border-line text-left">
              <th scope="col" className="py-2 pr-4 font-medium text-ink-muted">
                Zeitraum
              </th>
              {series.map((entry) => (
                <th
                  key={entry.regionId}
                  scope="col"
                  className="py-2 pr-4 font-medium text-ink-muted whitespace-nowrap"
                >
                  {entry.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {periods.map((period) => (
              <tr key={period} className="border-b border-line/60 last:border-0">
                <th
                  scope="row"
                  className="py-1.5 pr-4 text-left font-normal whitespace-nowrap text-ink-soft"
                >
                  {formatPeriod(period)}
                </th>
                {series.map((entry) => (
                  <td
                    key={entry.regionId}
                    className="py-1.5 pr-4 whitespace-nowrap tabular-nums text-ink"
                  >
                    {formatMetric(entry.values[period] ?? null, metric)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}
