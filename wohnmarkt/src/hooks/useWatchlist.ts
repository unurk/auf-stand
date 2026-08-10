"use client";

import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "presse-wohnmarkt.watchlist.v1";

/** Andere Komponenten im selben Tab über eine Änderung informieren. */
const CHANGE_EVENT = "presse-wohnmarkt:watchlist";

function readStorage(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    // Defensiv: nur Strings übernehmen, Duplikate entfernen.
    return [...new Set(parsed.filter((v): v is string => typeof v === "string"))];
  } catch {
    // Kaputter oder blockierter Storage darf die App nicht umbringen.
    return [];
  }
}

function writeStorage(regionIds: string[]): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(regionIds));
  } catch {
    // Privater Modus / voller Storage: still ignorieren, State bleibt in der Session.
  }
}

/**
 * Persönliche Beobachtungsliste, gespeichert im localStorage des Browsers.
 * Kein Login, kein Server, keine personenbezogenen Daten.
 *
 * `hydrated` verhindert, dass beim ersten Render (Server bzw. vor dem Lesen
 * des Storage) eine leere Liste als „du beobachtest nichts" fehlgedeutet wird.
 */
export function useWatchlist() {
  const [regionIds, setRegionIds] = useState<string[]>([]);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setRegionIds(readStorage());
    setHydrated(true);

    const sync = () => setRegionIds(readStorage());
    // storage: Änderung in einem anderen Tab. CHANGE_EVENT: im selben Tab.
    window.addEventListener("storage", sync);
    window.addEventListener(CHANGE_EVENT, sync);
    return () => {
      window.removeEventListener("storage", sync);
      window.removeEventListener(CHANGE_EVENT, sync);
    };
  }, []);

  const update = useCallback((next: string[]) => {
    setRegionIds(next);
    writeStorage(next);
    window.dispatchEvent(new Event(CHANGE_EVENT));
  }, []);

  const add = useCallback(
    (regionId: string) => {
      const current = readStorage();
      if (current.includes(regionId)) return;
      update([...current, regionId]);
    },
    [update],
  );

  const remove = useCallback(
    (regionId: string) => {
      update(readStorage().filter((id) => id !== regionId));
    },
    [update],
  );

  const toggle = useCallback(
    (regionId: string) => {
      const current = readStorage();
      update(
        current.includes(regionId)
          ? current.filter((id) => id !== regionId)
          : [...current, regionId],
      );
    },
    [update],
  );

  const isWatched = useCallback(
    (regionId: string) => regionIds.includes(regionId),
    [regionIds],
  );

  const clear = useCallback(() => update([]), [update]);

  return { regionIds, hydrated, add, remove, toggle, isWatched, clear };
}
