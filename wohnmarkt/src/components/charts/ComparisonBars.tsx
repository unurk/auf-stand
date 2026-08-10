"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { MetricKey } from "@/data/types";
import {
  METRIC_LABELS,
  formatAxisNumber,
  formatMetric,
  formatPeriod,
} from "@/lib/format";
import { SERIES_COLORS } from "./TimeSeriesChart";

export type BarEntry = {
  regionId: string;
  label: string;
  value: number;
};

/** Balkenvergleich des aktuellen Niveaus mehrerer Regionen. */
export function ComparisonBars({
  entries,
  metric,
  period,
}: {
  entries: BarEntry[];
  metric: MetricKey;
  period: string;
}) {
  const height = Math.max(180, entries.length * 44 + 40);

  return (
    <div
      style={{ height }}
      className="w-full"
      role="img"
      aria-label={`${METRIC_LABELS[metric]} im Vergleich, ${formatPeriod(period)}. ${entries
        .map((entry) => `${entry.label}: ${formatMetric(entry.value, metric)}`)
        .join("; ")}.`}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={entries}
          layout="vertical"
          margin={{ top: 4, right: 16, bottom: 4, left: 4 }}
        >
          <CartesianGrid stroke="#e2ded7" strokeDasharray="3 3" horizontal={false} />
          <XAxis
            type="number"
            tick={{ fontSize: 11, fill: "#6c727e" }}
            stroke="#cec8be"
            tickFormatter={(value: number) => formatAxisNumber(value, metric)}
          />
          <YAxis
            type="category"
            dataKey="label"
            width={124}
            tick={{ fontSize: 12, fill: "#4a4f5a" }}
            stroke="#cec8be"
          />
          <Tooltip
            formatter={(value) => formatMetric(value as number, metric)}
            contentStyle={{
              borderRadius: 8,
              border: "1px solid #e2ded7",
              fontSize: 13,
            }}
          />
          {/* Eine Farbe für alle Balken: Sie zeigen dieselbe Kennzahl, nur für
              verschiedene Regionen — wechselnde Farben würden eine Einteilung
              suggerieren, die es nicht gibt. */}
          <Bar
            dataKey="value"
            name={METRIC_LABELS[metric]}
            fill={SERIES_COLORS[0]}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
