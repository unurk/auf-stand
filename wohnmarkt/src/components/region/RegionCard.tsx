import Link from "next/link";
import type { Region } from "@/data/types";
import { getObservations } from "@/data";
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
import { WatchButton } from "./WatchButton";

/**
 * Kompakte Regionskarte. Alle Zahlen werden hier aus den Daten berechnet —
 * nichts davon steht als Text in der Datei.
 */
export function RegionCard({ region }: { region: Region }) {
  const series = getObservations(region.id);
  const latestSale = latestWithValue(series, "salePricePerSqm");
  const salePrice = metricValue(latestSale, "salePricePerSqm");
  const rentPrice = metricValue(
    latestWithValue(series, "rentPricePerSqm"),
    "rentPricePerSqm",
  );
  const listings = metricValue(
    latestWithValue(series, "listingsCount"),
    "listingsCount",
  );
  const saleChange = changeVsPrevious(series, "salePricePerSqm");

  return (
    <article className="flex flex-col rounded-lg border border-line bg-surface p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-editorial text-lg leading-snug text-ink">
            <Link
              href={`/regionen/${region.id}`}
              className="hover:text-accent hover:underline underline-offset-4"
            >
              {region.name}
            </Link>
          </h3>
          <p className="mt-0.5 text-xs text-ink-muted">{region.state}</p>
        </div>
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
        <div>
          <dt className="text-xs text-ink-muted">Kauf</dt>
          <dd className="mt-0.5 tabular-nums text-ink">
            {formatSalePerSqm(salePrice)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-ink-muted">Miete</dt>
          <dd className="mt-0.5 tabular-nums text-ink">
            {formatRentPerSqm(rentPrice)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-ink-muted">Inserate</dt>
          <dd className="mt-0.5 tabular-nums text-ink">{formatCount(listings)}</dd>
        </div>
        <div>
          <dt className="text-xs text-ink-muted">Kauf ggü. Vormonat</dt>
          <dd className="mt-0.5">
            <ChangeBadge change={saleChange} metric="salePricePerSqm" />
          </dd>
        </div>
      </dl>

      <p className="mt-3 text-xs text-ink-muted">
        Stand: {formatPeriod(latestSale?.period)}
      </p>

      <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-line pt-4">
        <WatchButton regionId={region.id} regionName={region.name} size="small" />
        <Link
          href={`/regionen/${region.id}`}
          className="text-sm font-medium text-accent underline underline-offset-2 hover:text-accent-dark"
        >
          Details
        </Link>
      </div>
    </article>
  );
}
