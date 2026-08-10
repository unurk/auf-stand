"use client";

import { useWatchlist } from "@/hooks/useWatchlist";

/**
 * „Region beobachten“ — schreibt in die lokale Beobachtungsliste.
 * Der Zustand steht als aria-pressed und im Text, nicht nur in der Farbe.
 */
export function WatchButton({
  regionId,
  regionName,
  size = "default",
}: {
  regionId: string;
  regionName: string;
  size?: "default" | "small";
}) {
  const { isWatched, toggle, hydrated } = useWatchlist();
  const watched = isWatched(regionId);

  const classes =
    size === "small"
      ? "px-2.5 py-1 text-xs"
      : "px-4 py-2 text-sm";

  return (
    <button
      type="button"
      onClick={() => toggle(regionId)}
      disabled={!hydrated}
      aria-pressed={watched}
      className={`inline-flex items-center gap-1.5 rounded-md border font-medium transition-colors disabled:opacity-50 ${classes} ${
        watched
          ? "border-accent bg-accent text-white hover:bg-accent-dark"
          : "border-line-strong bg-surface text-ink-soft hover:border-accent hover:text-accent"
      }`}
    >
      <span aria-hidden="true">{watched ? "✓" : "+"}</span>
      <span>
        {watched ? "Wird beobachtet" : "Region beobachten"}
        <span className="sr-only">: {regionName}</span>
      </span>
    </button>
  );
}
