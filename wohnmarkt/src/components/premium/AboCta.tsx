"use client";

import Link from "next/link";
import { usePremium } from "@/hooks/usePremium";

/**
 * Hinweis auf den Abo-Nutzwert. Dezent, sachlich, ohne Dringlichkeit —
 * und ohne Preise, Rabatte oder Bedingungen: dazu ist im Prototyp nichts
 * entschieden, und Erfundenes wäre irreführend.
 */
export function AboCta({
  title = "Deine Wohnmarkt-Beobachtung freischalten",
  description = "Verfolge mehrere Regionen regelmäßig und erhalte die vollständige Analyse im Presse Wohnmarkt-Update.",
  compact = false,
}: {
  title?: string;
  description?: string;
  compact?: boolean;
}) {
  const { isPremium, hydrated, set } = usePremium();

  if (hydrated && isPremium) return null;

  return (
    <section
      aria-label="Hinweis zum Abo-Nutzwert"
      className={`rounded-lg border border-accent/25 bg-accent/[0.04] ${
        compact ? "p-4" : "p-5 sm:p-6"
      }`}
    >
      <h2 className="font-editorial text-lg leading-snug text-ink">{title}</h2>
      <p className="mt-1.5 max-w-prose text-sm leading-relaxed text-ink-soft">
        {description}
      </p>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => set(true)}
          disabled={!hydrated}
          className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-dark disabled:opacity-50"
        >
          Abo-Ansicht simulieren
        </button>
        <Link
          href="/abo"
          className="text-sm font-medium text-accent underline underline-offset-2 hover:text-accent-dark"
        >
          Was im Abo enthalten wäre
        </Link>
      </div>
      <p className="mt-3 text-xs text-ink-muted">
        Simulation ohne Kauf: Es findet kein Bestellvorgang statt, es werden
        keine Preise oder Vertragsbedingungen dargestellt.
      </p>
    </section>
  );
}
