import type { ChangeResult } from "@/lib/metrics";
import type { MetricKey } from "@/data/types";
import {
  KEINE_DATEN,
  changeDirection,
  formatMetricDelta,
  formatPercent,
  formatPeriod,
} from "@/lib/format";

const DIRECTION_TEXT = {
  up: "gestiegen",
  down: "gesunken",
  flat: "unverändert",
  unknown: "unbekannt",
} as const;

const DIRECTION_SYMBOL = {
  up: "▲",
  down: "▼",
  flat: "▬",
  unknown: "–",
} as const;

/**
 * Zeigt eine Veränderung als Prozentwert.
 *
 * Farbe ist nie der einzige Bedeutungsträger: Richtung wird zusätzlich über
 * ein Symbol und über den Screenreader-Text ausgedrückt. „Steigend“ wird
 * bewusst nicht als gut oder schlecht gewertet — das hängt davon ab, ob man
 * kauft oder verkauft.
 */
export function ChangeBadge({
  change,
  metric,
  showAbsolute = false,
}: {
  change: ChangeResult | null;
  metric: MetricKey;
  showAbsolute?: boolean;
}) {
  if (!change) {
    return (
      <span className="text-sm text-ink-muted">{KEINE_DATEN}</span>
    );
  }

  const direction = changeDirection(change.percent);
  const color =
    direction === "up"
      ? "text-up"
      : direction === "down"
        ? "text-down"
        : "text-ink-soft";

  return (
    <span className={`inline-flex items-baseline gap-1.5 text-sm font-medium ${color}`}>
      <span aria-hidden="true">{DIRECTION_SYMBOL[direction]}</span>
      <span>{formatPercent(change.percent)}</span>
      {showAbsolute && (
        <span className="text-ink-muted font-normal">
          ({formatMetricDelta(change.absolute, metric)})
        </span>
      )}
      <span className="sr-only">
        {DIRECTION_TEXT[direction]} gegenüber {formatPeriod(change.fromPeriod)}
      </span>
    </span>
  );
}
