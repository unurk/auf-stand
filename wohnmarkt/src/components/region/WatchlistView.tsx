"use client";

import Link from "next/link";
import type { MarketObservation, Region } from "@/data/types";
import {
  changeVsPrevious,
  latestWithValue,
  metricValue,
} from "@/lib/metrics";
import {
  formatCount,
  formatPeriod,
  formatRentPerSqm,
  formatSalePerSqm,
} from "@/lib/format";
import { ChangeBadge } from "@/components/ui/ChangeBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { useWatchlist } from "@/hooks/useWatchlist";

/**
 * Persönliche Beobachtungsliste. Die Auswahl liegt im localStorage dieses
 * Browsers; die Kennzahlen kommen aus derselben Datenbasis wie überall sonst.
 */
export function WatchlistView({
  regions,
  seriesByRegion,
}: {
  regions: Region[];
  seriesByRegion: Record<string, MarketObservation[]>;
}) {
  const { regionIds, hydrated, remove, clear } = useWatchlist();

  if (!hydrated) {
    return (
      <div
        className="rounded-lg border border-line bg-surface p-6 text-sm text-ink-muted"
        aria-busy="true"
      >
        Beobachtungsliste wird geladen …
      </div>
    );
  }

  const watched = regionIds
    .map((id) => regions.find((region) => region.id === id))
    .filter((region): region is Region => Boolean(region));

  if (watched.length === 0) {
    return (
      <EmptyState
        title="Noch keine Region beobachtet"
        description="Wähle Regionen aus, die dich betreffen — etwa deinen Wohnort und einen möglichen Ausweichstandort. Beim nächsten Update siehst du hier sofort, was sich dort verändert hat."
        action={
          <Link
            href="/regionen"
            className="inline-block rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-dark"
          >
            Regionen ansehen
          </Link>
        }
      />
    );
  }

  return (
    <div className="space-y-4">
      <ul className="space-y-3">
        {watched.map((region) => {
          const series = seriesByRegion[region.id] ?? [];
          const latestSale = latestWithValue(series, "salePricePerSqm");
          const sale = metricValue(latestSale, "salePricePerSqm");
          const rent = metricValue(
            latestWithValue(series, "rentPricePerSqm"),
            "rentPricePerSqm",
          );
          const listings = metricValue(
            latestWithValue(series, "listingsCount"),
            "listingsCount",
          );

          return (
            <li
              key={region.id}
              className="rounded-lg border border-line bg-surface p-5"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-editorial text-lg leading-snug text-ink">
                    <Link
                      href={`/regionen/${region.id}`}
                      className="hover:text-accent hover:underline underline-offset-4"
                    >
                      {region.name}
                    </Link>
                  </h3>
                  <p className="mt-0.5 text-xs text-ink-muted">
                    {region.state} · Letztes Update {formatPeriod(latestSale?.period)}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => remove(region.id)}
                  className="rounded-md border border-line-strong px-3 py-1.5 text-xs font-medium text-ink-soft hover:border-accent hover:text-accent"
                >
                  Entfernen
                  <span className="sr-only">: {region.name}</span>
                </button>
              </div>

              <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-sm sm:grid-cols-4">
                <div>
                  <dt className="text-xs text-ink-muted">Kauf</dt>
                  <dd className="mt-0.5 tabular-nums text-ink">
                    {formatSalePerSqm(sale)}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-ink-muted">Letzte Veränderung</dt>
                  <dd className="mt-0.5">
                    <ChangeBadge
                      change={changeVsPrevious(series, "salePricePerSqm")}
                      metric="salePricePerSqm"
                      showAbsolute
                    />
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-ink-muted">Miete</dt>
                  <dd className="mt-0.5 tabular-nums text-ink">
                    {formatRentPerSqm(rent)}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-ink-muted">Inserate</dt>
                  <dd className="mt-0.5 tabular-nums text-ink">
                    {formatCount(listings)}
                  </dd>
                </div>
              </dl>

              <div className="mt-4 border-t border-line pt-3">
                <Link
                  href={`/regionen/${region.id}`}
                  className="text-sm font-medium text-accent underline underline-offset-2 hover:text-accent-dark"
                >
                  Zur Detailansicht
                </Link>
              </div>
            </li>
          );
        })}
      </ul>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-ink-muted">
          {watched.length} {watched.length === 1 ? "Region" : "Regionen"} beobachtet ·
          gespeichert im Browser dieses Geräts
        </p>
        <button
          type="button"
          onClick={clear}
          className="text-xs text-ink-muted underline underline-offset-2 hover:text-ink"
        >
          Liste leeren
        </button>
      </div>
    </div>
  );
}
