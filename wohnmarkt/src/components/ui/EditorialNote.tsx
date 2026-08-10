import type { EditorialInsight } from "@/data/types";
import { DemoBadge } from "./DemoBadge";

/**
 * Redaktionelle Einordnung. Bewusst optisch klar von den Datenblöcken
 * getrennt (eigene Fläche, Serifenschrift, eigene Kennzeichnung): Daten und
 * Deutung dürfen im Produkt nicht ineinanderlaufen.
 */
export function EditorialNote({
  insight,
  variant = "full",
}: {
  insight: EditorialInsight | undefined;
  variant?: "full" | "summary";
}) {
  if (!insight) {
    return (
      <div className="rounded-lg border border-line bg-surface p-5 text-sm text-ink-muted">
        Für diesen Zeitraum liegt keine redaktionelle Einordnung vor.
      </div>
    );
  }

  return (
    <article className="rounded-lg border-l-4 border-l-accent border-y border-r border-line bg-surface p-5 sm:p-6">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium tracking-wide text-accent uppercase">
          Redaktionelle Einordnung
        </span>
        {insight.isDemo && <DemoBadge label="Demo-Text" />}
      </div>
      <h3 className="mt-2 font-editorial text-xl leading-snug text-ink">
        {insight.title}
      </h3>
      <p className="mt-2 font-editorial text-base leading-relaxed text-ink-soft">
        {insight.summary}
      </p>
      {variant === "full" && (
        <p className="mt-3 font-editorial text-base leading-relaxed text-ink-soft">
          {insight.body}
        </p>
      )}
    </article>
  );
}
