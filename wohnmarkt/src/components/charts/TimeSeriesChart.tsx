"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { MetricKey } from "@/data/types";
import {
  METRIC_LABELS,
  METRIC_UNITS,
  formatAxisNumber,
  formatMetric,
  formatPeriod,
  formatPeriodShort,
} from "@/lib/format";

/** Farbfolge für Regionsreihen — auch bei Farbfehlsichtigkeit unterscheidbar. */
export const SERIES_COLORS = [
  "#2d4f9e",
  "#b45309",
  "#0f766e",
  "#7c2d70",
] as const;

export type ChartSeries = {
  regionId: string;
  label: string;
};

export type ChartRow = {
  period: string;
  /** Wert je regionId; fehlende Werte als null → Recharts unterbricht die Linie. */
  values: Record<string, number | null>;
};

/**
 * Zeitreihe für eine oder mehrere Regionen.
 * Lücken bleiben Lücken: null-Werte werden nicht interpoliert.
 */
export function TimeSeriesChart({
  rows,
  series,
  metric,
  description,
}: {
  rows: ChartRow[];
  series: ChartSeries[];
  metric: MetricKey;
  description: string;
}) {
  const data = rows.map((row) => ({
    period: row.period,
    label: formatPeriodShort(row.period),
    ...row.values,
  }));

  return (
    <div
      className="h-64 w-full sm:h-80"
      role="img"
      aria-label={`${METRIC_LABELS[metric]} im Zeitverlauf. ${description}`}
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
          <CartesianGrid stroke="#e2ded7" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11, fill: "#6c727e" }}
            stroke="#cec8be"
            interval="preserveStartEnd"
            minTickGap={18}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "#6c727e" }}
            stroke="#cec8be"
            width={64}
            domain={["auto", "auto"]}
            tickFormatter={(value: number) => formatAxisNumber(value, metric)}
          />
          <Tooltip
            formatter={(value) => formatMetric(value as number, metric)}
            labelFormatter={(_label, payload) =>
              formatPeriod(payload?.[0]?.payload?.period as string)
            }
            contentStyle={{
              borderRadius: 8,
              border: "1px solid #e2ded7",
              fontSize: 13,
            }}
          />
          {series.length > 1 && <Legend wrapperStyle={{ fontSize: 12 }} />}
          {series.map((entry, index) => (
            <Line
              key={entry.regionId}
              type="monotone"
              dataKey={entry.regionId}
              name={entry.label}
              stroke={SERIES_COLORS[index % SERIES_COLORS.length]}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              connectNulls={false}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
      <p className="sr-only">Einheit: {METRIC_UNITS[metric]}</p>
    </div>
  );
}
