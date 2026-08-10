"use client";

import { usePremium } from "@/hooks/usePremium";

/**
 * Umschalter zwischen freiem und simuliertem Abo-Zustand.
 * Ausdrücklich ein Prototyp-Werkzeug für den Review, kein Produktelement.
 */
export function PremiumToggle() {
  const { isPremium, hydrated, toggle } = usePremium();

  return (
    <div className="flex items-center gap-3 rounded-lg border border-line bg-paper px-3 py-2">
      <div className="text-right">
        <div className="text-[11px] font-medium tracking-wide text-ink-muted uppercase">
          Ansicht (Demo)
        </div>
        <div className="text-sm text-ink" aria-live="polite">
          {!hydrated ? "wird geladen …" : isPremium ? "Abo simuliert" : "Frei zugänglich"}
        </div>
      </div>
      <button
        type="button"
        onClick={toggle}
        disabled={!hydrated}
        aria-pressed={isPremium}
        className="rounded-md border border-accent px-3 py-1.5 text-sm font-medium text-accent transition-colors hover:bg-accent hover:text-white disabled:opacity-50"
      >
        {isPremium ? "Zurück auf frei" : "Abo simulieren"}
      </button>
    </div>
  );
}
