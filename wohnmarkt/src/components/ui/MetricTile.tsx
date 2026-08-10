import type { ReactNode } from "react";
import { KEINE_DATEN } from "@/lib/format";

/**
 * Eine Kennzahl mit Bezeichnung, Wert, Zeitbezug und optionaler Veränderung.
 * Der Wert kommt immer schon formatiert herein (aus src/lib/format.ts).
 */
export function MetricTile({
  label,
  value,
  note,
  change,
  hint,
}: {
  label: string;
  value: string;
  note?: string;
  change?: ReactNode;
  hint?: string;
}) {
  const missing = value === KEINE_DATEN;

  return (
    <div className="rounded-lg border border-line bg-surface p-4">
      <div className="text-xs font-medium tracking-wide text-ink-muted uppercase">
        {label}
      </div>
      <div
        className={`mt-1.5 font-editorial text-2xl leading-tight ${
          missing ? "text-ink-muted text-base italic" : "text-ink"
        }`}
      >
        {value}
      </div>
      {change && <div className="mt-1.5">{change}</div>}
      {note && <div className="mt-1 text-xs text-ink-muted">{note}</div>}
      {hint && missing && (
        <p className="mt-2 text-xs text-ink-muted">{hint}</p>
      )}
    </div>
  );
}
