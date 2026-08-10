"use client";

import type { ReactNode } from "react";
import { usePremium } from "@/hooks/usePremium";
import { AboCta } from "./AboCta";

/**
 * Simulierte Abo-Schranke. Im freien Zustand wird der Inhalt nicht gerendert
 * und stattdessen erklärt, was das Abo an dieser Stelle zeigen würde —
 * eine optische Unschärfe über echten Inhalten wäre unehrlich, weil die
 * Daten dann trotzdem im HTML stünden.
 */
export function PremiumGate({
  title,
  description,
  preview,
  children,
}: {
  title: string;
  description: string;
  /** Optionaler frei sichtbarer Ausschnitt oberhalb der Schranke. */
  preview?: ReactNode;
  children: ReactNode;
}) {
  const { isPremium, hydrated } = usePremium();

  if (!hydrated) {
    return (
      <div
        className="rounded-lg border border-line bg-surface p-6 text-sm text-ink-muted"
        aria-busy="true"
      >
        Ansicht wird geladen …
      </div>
    );
  }

  if (isPremium) return <>{children}</>;

  return (
    <div className="space-y-4">
      {preview}
      <div className="rounded-lg border border-line bg-surface p-5 sm:p-6">
        <div className="flex flex-wrap items-center gap-2">
          <span aria-hidden="true" className="text-ink-muted">
            ◈
          </span>
          <span className="text-xs font-medium tracking-wide text-ink-muted uppercase">
            Im Abo enthalten (simuliert)
          </span>
        </div>
        <h3 className="mt-2 font-editorial text-lg leading-snug text-ink">
          {title}
        </h3>
        <p className="mt-1.5 max-w-prose text-sm leading-relaxed text-ink-soft">
          {description}
        </p>
        <div className="mt-4">
          <AboCta compact />
        </div>
      </div>
    </div>
  );
}
